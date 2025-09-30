import pandas as pd
import joblib
import os
import logging
import sys
from datetime import datetime, timedelta
from supabase import create_client
from dotenv import load_dotenv

# Add debug print at the very start
print("🚀 Script started - importing modules...")

try:
    from fleet_analytics import MetroFleetAnalytics
    print("✅ Successfully imported MetroFleetAnalytics")
except ImportError as e:
    print(f"❌ Failed to import MetroFleetAnalytics: {e}")
    print(f"🔍 Python path: {sys.path}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

MODELS_DIR = "ai_railway_project/models"


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE1_URL")
SUPABASE_KEY = os.getenv("SUPABASE1_KEY")  # should be service_role key for write access
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)



# --- Load ML models ---
def load_models():
    print("🔧 Starting to load models...")
    models = {}
    try:
        models['status_classifier'] = joblib.load(os.path.join(MODELS_DIR, 'assigned_status_classifier.pkl'))
        models['failure_regressor'] = joblib.load(os.path.join(MODELS_DIR, 'failure_risk_regressor.pkl'))
        models['mileage_regressor'] = joblib.load(os.path.join(MODELS_DIR, 'mileage_regressor.pkl'))
        models['status_encoder'] = joblib.load(os.path.join(MODELS_DIR, 'status_label_encoder.pkl'))
        logging.info("All models loaded successfully.")
        return models
    except FileNotFoundError as e:
        logging.error(f"Error loading model: {e}")
        return None

# --- Preprocess ---
def preprocess_for_prediction(df, historical_columns):
    df_processed = df.copy()
    df_processed.drop(columns=['dayid','train_id','date','last_maintenance_date','assigned_status'], inplace=True, errors='ignore')
    df_processed = pd.get_dummies(df_processed, columns=['depot','cleaning_slot','stabling_position'], drop_first=True)
    df_processed = df_processed.reindex(columns=historical_columns, fill_value=0)
    return df_processed.fillna(0)

# --- Make predictions ---
def make_predictions(models, data):
    if models is None or data.empty:
        logging.error("Models not loaded or empty data.")
        return None
    
    try:
        status_features = models['status_classifier'].feature_names_in_
        failure_features = models['failure_regressor'].feature_names_in_
        mileage_features = models['mileage_regressor'].feature_names_in_
        all_features = list(set(list(status_features)) | set(list(failure_features)) | set(list(mileage_features)))
        processed_data = preprocess_for_prediction(data.copy(), all_features)

        status_pred_encoded = models['status_classifier'].predict(processed_data[status_features])
        failure_risk = models['failure_regressor'].predict(processed_data[failure_features])
        next_day_mileage = models['mileage_regressor'].predict(processed_data[mileage_features])

        data['predicted_status'] = models['status_encoder'].inverse_transform(status_pred_encoded)
        data['predicted_failure_risk'] = failure_risk.round(4)
        data['predicted_next_day_mileage'] = next_day_mileage.round(2)
        return data
    except Exception as e:
        print(f"❌ Error during prediction: {e}")
        return None

# --- Generate Initial Schedule ---
def generate_initial_schedule(predictions_df, fleet_analytics):
    print("⚙️ Generating initial optimized schedule...")
    predictions_df['final_status'] = predictions_df['predicted_status']

    # Hard constraints → IBL
    predictions_df.loc[
        (predictions_df['job_critical_count'] > 0) |
        (predictions_df['rs_days_from_plan'] <= 0) |
        (predictions_df['sig_days_from_plan'] <= 0) |
        (predictions_df['tel_days_from_plan'] <= 0) |
        (predictions_df['manual_override_flag'] == 1),
        'final_status'
    ] = 'IBL'

    ibl_trains = predictions_df[predictions_df['final_status']=='IBL'].copy()
    eligible_trains = predictions_df[predictions_df['final_status']!='IBL'].copy()

    # Get fleet allocation targets but CAP Service at 14
    fa = fleet_analytics.fleet_allocation_justification()
    TARGET_SERVICE_COUNT = min(fa['min_service_trains'], len(eligible_trains))
    MAX_SERVICE_TRAINS = 14
    if TARGET_SERVICE_COUNT > MAX_SERVICE_TRAINS:
        TARGET_SERVICE_COUNT = MAX_SERVICE_TRAINS

    # Rank eligible trains by combined score
    avg_mileage = eligible_trains['predicted_next_day_mileage'].mean()
    def combined_score(row):
        reliability_score = 1 - row['predicted_failure_risk']
        passenger_exp_score = 100 - (row['hvac_alert'] * 25) - max(0, row['iot_temp_avg_c']-28)*10
        bogie_score = 1 - row['bogie_wear_index']
        mileage_factor = 1 - min(row['predicted_next_day_mileage'] / (avg_mileage*1.2), 1)
        return reliability_score*0.35 + (passenger_exp_score/100)*0.25 + bogie_score*0.2 + mileage_factor*0.2

    eligible_trains['combined_score'] = eligible_trains.apply(combined_score, axis=1)
    eligible_trains = eligible_trains.sort_values(by='combined_score', ascending=False).reset_index(drop=True)

    # Assign Service trains
    eligible_trains.loc[eligible_trains.index[:TARGET_SERVICE_COUNT], 'final_status'] = 'Service'

    # Assign Standby trains (all remaining eligible trains)
    remaining_after_service = eligible_trains.iloc[TARGET_SERVICE_COUNT:]
    if len(remaining_after_service) > 0:
        eligible_trains.loc[eligible_trains.index[TARGET_SERVICE_COUNT:], 'final_status'] = 'Standby'

    # Combine with original IBL trains
    final_schedule = pd.concat([eligible_trains.drop(columns=['combined_score'], errors='ignore'), ibl_trains])
    final_schedule = final_schedule.sort_values(by='final_status', key=lambda x: x.map({'Service':0,'Standby':1,'IBL':2})).reset_index(drop=True)
    final_schedule['ranking'] = final_schedule.index + 1

    return final_schedule

# --- Display Schedule with Highlights ---
def display_schedule(schedule, title, highlight_changes=False, original_schedule=None):
    print(f"\n" + "="*80)
    print(f"🚆  {title}".center(80))
    print("="*80 + "\n")
    
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', None)
    
    display_columns = ['ranking', 'train_id', 'final_status', 'predicted_status', 'predicted_failure_risk']
    if 'manual_override_flag' in schedule.columns:
        display_columns.append('manual_override_flag')
    
    if highlight_changes and original_schedule is not None:
        # Create a copy for display with change indicators
        display_df = schedule[display_columns].copy()
        display_df['change'] = ''
        
        for idx, train in schedule.iterrows():
            original_train = original_schedule[original_schedule['train_id'] == train['train_id']]
            if not original_train.empty:
                original_status = original_train['final_status'].iloc[0]
                if original_status != train['final_status']:
                    display_df.at[idx, 'change'] = f'🔄 {original_status}→{train["final_status"]}'
                elif train.get('manual_override_flag', False) == True:
                    display_df.at[idx, 'change'] = '🎮 OVERRIDE'
        
        # Reorder columns to show change last
        display_columns_with_change = display_columns + ['change']
        print(display_df[display_columns_with_change].to_string(index=False))
    else:
        print(schedule[display_columns].to_string(index=False))
    
    pd.reset_option('display.max_rows')
    pd.reset_option('display.width')
    
    # Show summary
    service_count = len(schedule[schedule['final_status'] == 'Service'])
    standby_count = len(schedule[schedule['final_status'] == 'Standby'])
    ibl_count = len(schedule[schedule['final_status'] == 'IBL'])
    print(f"\n📊 SUMMARY: {service_count} Service, {standby_count} Standby, {ibl_count} IBL")

# --- Interactive Modification System ---
# --- Interactive Modification System ---
def interactive_modification_system(initial_schedule, fleet_analytics):
    """
    Allow user to modify the schedule interactively with safety checks
    """
    print("\n🎮 INTERACTIVE SCHEDULE MODIFICATION")
    print("="*50)
    
    current_schedule = initial_schedule.copy()
    modification_log = []
    
    while True:
        print("\n📋 MODIFICATION OPTIONS:")
        print("   [1] Force train to Service")
        print("   [2] Force train to Standby") 
        print("   [3] Force train to IBL")
        print("   [4] Reset train to predicted status")
        print("   [5] Show current schedule")
        print("   [6] Show modification log")
        print("   [7] What-If Analysis")
        print("   [8] Finish modifications")  # Moved to last position
        
        choice = input("\n   Select option (1-8): ").strip()
        
        if choice == '1':
            train_id = input("   Enter Train ID to force to Service: ").strip().upper()
            if train_id in current_schedule['train_id'].values:
                original_status = current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'].iloc[0]
                
                # SAFETY CHECK: Prevent IBL → Service
                if original_status == 'IBL':
                    print(f"   🚨 SAFETY VIOLATION: Cannot force IBL train {train_id} to Service!")
                    print(f"   ❌ IBL trains have safety/maintenance issues and cannot be used")
                    continue
                
                risk = current_schedule.loc[current_schedule['train_id'] == train_id, 'predicted_failure_risk'].iloc[0]
                
                # WARNING for high-risk trains
                if risk > 0.3:
                    confirm = input(f"   ⚠️  WARNING: High failure risk ({risk:.1%}). Continue? (y/n): ").strip().lower()
                    if confirm != 'y':
                        print("   ❌ Operation cancelled")
                        continue
                
                current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'] = 'Service'
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_flag'] = True
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_status'] = 'Service'
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_reason'] = 'Interactive override'
                
                modification_log.append(f"🚆 {train_id}: {original_status} → Service (Manual override)")
                print(f"   ✅ {train_id} forced to Service")
                
            else:
                print(f"   ❌ Train {train_id} not found")
                
        elif choice == '2':
            train_id = input("   Enter Train ID to force to Standby: ").strip().upper()
            if train_id in current_schedule['train_id'].values:
                original_status = current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'].iloc[0]
                
                # SAFETY CHECK: Prevent IBL → Standby
                if original_status == 'IBL':
                    print(f"   🚨 SAFETY VIOLATION: Cannot force IBL train {train_id} to Standby!")
                    print(f"   ❌ IBL trains have safety/maintenance issues and cannot be used as standby")
                    continue
                
                current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'] = 'Standby'
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_flag'] = 1
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_status'] = 'Standby'
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_reason'] = 'Interactive override'
                
                modification_log.append(f"🚆 {train_id}: {original_status} → Standby (Manual override)")
                print(f"   ✅ {train_id} forced to Standby")
            else:
                print(f"   ❌ Train {train_id} not found")
                
        elif choice == '3':
            train_id = input("   Enter Train ID to force to IBL: ").strip().upper()
            if train_id in current_schedule['train_id'].values:
                original_status = current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'].iloc[0]
                
                # Allow Service/Standby → IBL (safe operation)
                current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'] = 'IBL'
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_flag'] = 1
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_status'] = 'IBL'
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_reason'] = 'Interactive override'
                
                modification_log.append(f"🚆 {train_id}: {original_status} → IBL (Manual override)")
                print(f"   ✅ {train_id} forced to IBL")
                
                # Inform if this was a Service train
                if original_status == 'Service':
                    print(f"   ℹ️  Service capacity reduced by 1 train")
                    
            else:
                print(f"   ❌ Train {train_id} not found")
                
        elif choice == '4':
            train_id = input("   Enter Train ID to reset to predicted status: ").strip().upper()
            if train_id in current_schedule['train_id'].values:
                original_status = current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'].iloc[0]
                predicted_status = current_schedule.loc[current_schedule['train_id'] == train_id, 'predicted_status'].iloc[0]
                current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'] = predicted_status
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_flag'] = 0
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_status'] = ''
                current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_reason'] = ''
                
                modification_log.append(f"🚆 {train_id}: {original_status} → {predicted_status} (Reset)")
                print(f"   ✅ {train_id} reset to predicted status: {predicted_status}")
            else:
                print(f"   ❌ Train {train_id} not found")
                
        elif choice == '5':
            display_schedule(current_schedule, "CURRENT MODIFIED SCHEDULE", True, initial_schedule)
            
        elif choice == '6':
            print("\n📝 MODIFICATION LOG:")
            if modification_log:
                for log in modification_log:
                    print(f"   • {log}")
            else:
                print("   No modifications yet")
                
        elif choice == '7':
            what_if_analysis(current_schedule, fleet_analytics)
            7

        elif choice == '8':
            print("   ✅ Finishing modifications...")
            break
            
        else:
            print("   ❌ Invalid option")
    
    return current_schedule, modification_log

# --- What-If Analysis ---
def what_if_analysis(schedule, fleet_analytics):
    """
    Interactive What-If scenario analysis
    """
    print("\n🔍 WHAT-IF SCENARIO ANALYSIS")
    print("="*50)
    
    scenarios = {
        '1': 'Force specific train to Service',
        '2': 'Simulate train failure',
        '3': 'Change maintenance schedule',
        '4': 'Adjust service hours/headway',
        '5': 'Back to main menu'
    }
    
    print("Available scenarios:")
    for key, desc in scenarios.items():
        print(f"   [{key}] {desc}")
    
    choice = input("\nSelect scenario (1-5): ").strip()
    
    if choice == '1':
        train_id = input("Enter Train ID to analyze forcing to Service: ").strip().upper()
        if train_id in schedule['train_id'].values:
            current_status = schedule.loc[schedule['train_id'] == train_id, 'final_status'].iloc[0]
            risk = schedule.loc[schedule['train_id'] == train_id, 'predicted_failure_risk'].iloc[0]
            
            print(f"\n🔍 ANALYSIS FOR {train_id}:")
            print(f"   Current status: {current_status}")
            print(f"   Failure risk: {risk:.1%}")
            
            if risk > 0.3:
                print(f"   ⚠️  HIGH RISK: Not recommended for Service")
            elif current_status == 'IBL':
                print(f"   🚨 SAFETY CONCERN: IBL train should not be forced to Service")
            else:
                print(f"   ✅ Can be safely forced to Service")
                
        else:
            print(f"❌ Train {train_id} not found")
            
    elif choice == '2':
        train_id = input("Enter Train ID to simulate failure: ").strip().upper()
        if train_id in schedule['train_id'].values:
            current_status = schedule.loc[schedule['train_id'] == train_id, 'final_status'].iloc[0]
            print(f"\n🔍 FAILURE SIMULATION FOR {train_id}:")
            print(f"   Current status: {current_status}")
            if current_status == 'Service':
                standby_count = len(schedule[schedule['final_status'] == 'Standby'])
                print(f"   🚨 SERVICE IMPACT: Requires immediate standby deployment")
                print(f"   📊 Available standby trains: {standby_count}")
                if standby_count == 0:
                    print(f"   ⚠️  CRITICAL: No standby trains available!")
            else:
                print(f"   ℹ️  Minimal service impact")
                
    elif choice == '3':
        high_risk = len(schedule[schedule['predicted_failure_risk'] > 0.25])
        print(f"\n🔍 MAINTENANCE DELAY ANALYSIS:")
        print(f"   High-risk trains (>25% failure risk): {high_risk}")
        if high_risk > 0:
            print(f"   ⚠️  {high_risk} trains would become critical")
        else:
            print(f"   ✅ No high-risk trains affected")
            
    elif choice == '4':
            # PROPER METRO HEADWAY CALCULATION
            try:
                total_fleet_size = 25
                current_headway = 7.5  # minutes
                service_hours = 16.5   # 06:00 to 22:30
                min_standby = 3
                avg_trip_duration = 2.0  # hours per round trip
                
                print(f"\n📊 METRO OPERATION PARAMETERS:")
                print(f"   Total fleet: {total_fleet_size} trains")
                print(f"   Service: 06:00-22:30 ({service_hours}h)")
                print(f"   Current headway: {current_headway} min")
                print(f"   Avg round trip: {avg_trip_duration}h")
                print(f"   Min standby: {min_standby} trains")
                
                new_headway = float(input("Enter new headway in minutes: ") or "10")
                
                if new_headway <= 0:
                    print("   ❌ Headway must be positive")
                    return
                
                # PROPER CALCULATION: Trains needed = (Trip time / Headway) + Buffer
                trains_needed = (avg_trip_duration * 60) / new_headway
                total_needed = trains_needed + min_standby
                
                print(f"\n🔍 HEADWAY ANALYSIS:")
                print(f"   Current: {current_headway} min → New: {new_headway} min")
                print(f"   Trains needed for service: {trains_needed:.1f}")
                print(f"   + {min_standby} standby = {total_needed:.1f} total needed")
                print(f"   Available fleet: {total_fleet_size} trains")
                
                if total_needed <= total_fleet_size:
                    service_trains = int(trains_needed)
                    standby_trains = min_standby
                    ibl_trains = total_fleet_size - service_trains - standby_trains
                    
                    print(f"   ✅ FEASIBLE")
                    print(f"\n📋 FLEET ALLOCATION:")
                    print(f"   Service: {service_trains} trains")
                    print(f"   Standby: {standby_trains} trains") 
                    print(f"   IBL: {ibl_trains} trains")
                    
                else:
                    shortage = total_needed - total_fleet_size
                    print(f"   🚨 NOT FEASIBLE - Shortage of {shortage:.1f} trains")
                    print(f"   💡 Maximum headway: {((avg_trip_duration * 60) / (total_fleet_size - min_standby)):.1f} min")
                    
            except ValueError:
                print("   ❌ Please enter a valid number")
        
    elif choice == '5':
        return
        
    input("\nPress Enter to continue...")

# --- Main ---
def main():
    print("\n" + "="*50)
    print("🚀 METRO SCHEDULE OPTIMIZATION STARTED")
    print("="*50)
    
    try:
        # Load data from Supabase daily_data table
        print("📥 Loading data from Supabase daily_data table...")
        
        # Get the latest data (assuming you want the most recent records)
        response = supabase.table('daily_data').select('*').execute()
        
        if not response.data:
            logging.error("No data found in daily_data table")
            print("❌ No data found in daily_data table")
            return
        
        # Convert to DataFrame
        simulated_data = pd.DataFrame(response.data)
        
        print(f"✅ Loaded {len(simulated_data)} records from daily_data table")
        
        # Check if we have the required columns
        required_columns = ['train_id', 'dayid', 'date']  # Add other required columns as needed
        missing_columns = [col for col in required_columns if col not in simulated_data.columns]
        
        if missing_columns:
            logging.error(f"Missing required columns in daily_data: {missing_columns}")
            print(f"❌ Missing required columns in daily_data: {missing_columns}")
            return
            
    except Exception as e:
        logging.error(f"Error loading data from Supabase: {e}")
        print(f"❌ Error loading data from Supabase: {e}")
        return

    # Load models
    models = load_models()
    if not models:
        return

    # Make predictions
    predictions = make_predictions(models, simulated_data)
    if predictions is None:
        return

    # Create fleet analytics and generate initial schedule
    fleet_analytics = MetroFleetAnalytics(predictions)
    initial_schedule = generate_initial_schedule(predictions, fleet_analytics)

    # STEP 1: Show initial optimized schedule
    display_schedule(initial_schedule, "INITIAL OPTIMIZED SCHEDULE")
    
    # STEP 2: Allow interactive modifications
    final_schedule, modification_log = interactive_modification_system(initial_schedule, fleet_analytics)
    
    # STEP 3: Show final modified schedule with changes highlighted
    if modification_log:
        display_schedule(final_schedule, "FINAL MODIFIED SCHEDULE", True, initial_schedule)
        
        print("\n📝 FINAL MODIFICATION SUMMARY:")
        for log in modification_log:
            print(f"   • {log}")
    else:
        display_schedule(final_schedule, "FINAL SCHEDULE (No Changes)")
        print("\n✅ No modifications were made")

    # Save final schedule
    output_path = "ai_railway_project/data/next_day_predictions_optimised.csv"
    final_schedule.to_csv(output_path, index=False)
    print(f"💾 Saved final schedule to {output_path}")

    # Generate analytics report
    analytics = MetroFleetAnalytics(final_schedule)
    report = analytics.generate_kmrl_report()
    
    # Custom print function for fleet report (you can keep your existing one)
    print_fleet_report_custom(report)
    
    print("\n" + "="*50)
    print("✅ METRO SCHEDULE OPTIMIZATION COMPLETED")
    print("="*50)

# You'll need to include your print_fleet_report_custom function here
def print_fleet_report_custom(report):
    print("\n" + "="*70)
    print("🚆  METRO FLEET ANALYTICS REPORT".center(70))
    print("="*70 + "\n")

    # Fleet Health Index
    print("🔹 FLEET HEALTH INDEX".ljust(40))
    print(f"   Score: {report['Fleet Health Index']}\n")

    # Predictive Maintenance Alerts
    print("🔹 PREDICTIVE MAINTENANCE ALERTS".ljust(40))
    if report['Predictive Maintenance Alerts']:
        for alert in report['Predictive Maintenance Alerts']:
            print(f"   Train {alert['train_id']} ({alert['depot']}):")
            for a_type, severity, val in alert['alerts']:
                print(f"      • {a_type} | Severity: {severity} | Value: {val}")
    else:
        print("   No critical alerts.")
    print()

    # Resource Optimization
    print("🔹 RESOURCE OPTIMIZATION SUGGESTIONS")
    if report['Resource Optimization Suggestions']:
        for suggestion in report['Resource Optimization Suggestions']:
            print(f"   • {suggestion}")
    else:
        print("   All depots optimized.")
    print()

    # Revenue Impact
    revenue = report['Revenue Impact']
    print("🔹 REVENUE IMPACT")
    print(f"   Out-of-Service Trains: {revenue['out_of_service']}")
    print(f"   Potential Revenue Loss: ₹{revenue['potential_loss']}")
    print(f"   Maintenance Cost Today: ₹{revenue['maint_cost_today']}")
    print(f"   Branding Shortfall Cost: ₹{revenue['branding_shortfall_cost']}\n")

    # Dynamic Route Assignment
    print("🔹 DYNAMIC ROUTE ASSIGNMENT")
    for route in report['Dynamic Route Assignment']:
        print(f"   Train {route['train_id']} → Route: {route['assigned_route']}, Reliability: {route['reliability']}")
    print()

    # Energy Efficiency
    print("🔹 ENERGY EFFICIENCY")
    for e in report['Energy Efficiency']:
        print(f"   Train {e['train_id']} → {e['kWh/100km']} kWh | Rating: {e['rating']} | Main Issue: {e['main_issue']}")
    print()

    # Passenger Experience
    print("🔹 PASSENGER EXPERIENCE")
    for p in report['Passenger Experience']:
        factors = ", ".join(p['factors'])
        print(f"   Train {p['train_id']} → Score: {p['score']} | Rating: {p['rating']} | Factors: {factors}")
    print()

    # Intelligent Maintenance Schedule
    print("🔹 INTELLIGENT MAINTENANCE SCHEDULE")
    for tid, sched in report['Intelligent Maintenance Schedule'].items():
        types = ", ".join(sched['types'])
        print(f"   Train {tid} → Priority: {sched['priority']} | Urgency: {sched['urgency']} | Types: {types} | Est. Hours: {sched['est_hours']}")
    print()

    # Fleet Allocation Justification
    fa = report['Fleet Allocation Justification']
    print("🔹 FLEET ALLOCATION JUSTIFICATION")
    print(f"   Total Fleet Size: {fa['fleet_size']}")
    print(f"   Minimum Service (Revenue) Trains: {fa['min_service_trains']}")
    print(f"   Minimum Standby Trains: {fa['min_standby_trains']}")
    print(f"   Minimum IBL Trains: {fa['min_ibl_trains']}")
    print(f"   Expected Revenue: ₹{fa['expected_revenue']}")
    print(f"   Note: {fa['note']}")
    print("\n" + "="*70 + "\n")
    
    

if __name__ == "__main__":
    main()