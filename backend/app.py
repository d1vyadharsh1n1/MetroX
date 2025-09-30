from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import threading
import time
from supabase import create_client
from dotenv import load_dotenv

# Add MetroX_309 path to import fleet analytics
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'MetroX_309', 'ai_railway_project', 'scripts'))
try:
    from fleet_analytics import MetroFleetAnalytics
    print("✅ Successfully imported MetroFleetAnalytics")
except ImportError as e:
    print(f"❌ Failed to import MetroFleetAnalytics: {e}")
    MetroFleetAnalytics = None

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables to store execution status and output
execution_status = {
    'is_running': False,
    'current_step': '',
    'output': [],
    'error': None,
    'last_execution': None
}

# Global variables for schedule data
current_schedule = None
initial_schedule = None
modification_log = []
fleet_analytics = None

# Supabase connection
load_dotenv()
SUPABASE_URL = "https://ulqaisxxraujxnmrkprp.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVscWFpc3h4cmF1anhubXJrcHJwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTE4MzE2NSwiZXhwIjoyMDc0NzU5MTY1fQ.-LXhEtjzG4EF07Z80NOeSn0xtzJsl71N1iroDw-yUDc"

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected successfully")
except Exception as e:
    print(f"❌ Supabase connection failed: {e}")
    supabase = None

def get_train_ids():
    """Generate train IDs"""
    return [f"KM-T{101 + i}" for i in range(25)]

def simulate_data_for_day(sim_date, prev_day_data=None):
    """Simulate daily train data"""
    train_ids = get_train_ids()
    data = []

    CRITICAL_JOB_PROB = [0.98, 0.015, 0.005]
    HVAC_ALERT_PROBS = [0.85, 0.15]

    for train_id in train_ids:
        if prev_day_data is not None and train_id in prev_day_data['train_id'].values:
            prev_row = prev_day_data[prev_day_data['train_id'] == train_id].iloc[0]
            mileage_km = prev_row['mileage_km'] + np.random.randint(100, 500)
            bogie_wear_index = min(prev_row['bogie_wear_index'] + np.random.uniform(0.001, 0.01), 1.0)
            rs_days_from_plan = max(prev_row['rs_days_from_plan'] - 1, -5)
            sig_days_from_plan = max(prev_row['sig_days_from_plan'] - 1, -5)
            tel_days_from_plan = max(prev_row['tel_days_from_plan'] - 1, -5)
            prev_night_shunting_count = np.random.randint(0, 4)
            last_maintenance_date = prev_row['last_maintenance_date']
        else:
            mileage_km = np.random.randint(1500, 10000)
            bogie_wear_index = round(np.random.uniform(0.1, 0.8), 4)
            rs_days_from_plan = np.random.randint(1, 90)
            sig_days_from_plan = np.random.randint(1, 90)
            tel_days_from_plan = np.random.randint(1, 90)
            prev_night_shunting_count = np.random.randint(0, 4)
            last_maintenance_date = (sim_date - timedelta(days=np.random.randint(1, 90))).strftime('%Y-%m-%d')

        record = {
            "dayid": f"{sim_date.strftime('%d-%m')}-{train_id}",
            "date": sim_date.strftime('%Y-%m-%d'),
            "train_id": train_id,
            "depot": np.random.choice(["Pettah Depot", "Tripunithura Depot"]),
            "rs_days_from_plan": rs_days_from_plan,
            "sig_days_from_plan": sig_days_from_plan,
            "tel_days_from_plan": tel_days_from_plan,
            "job_open_count": np.random.randint(0, 10),
            "job_critical_count": int(np.random.choice([0, 1, 2], p=CRITICAL_JOB_PROB)),
            "branding_req_hours": round(np.random.uniform(5, 18), 2),
            "branding_alloc_hours": round(np.random.uniform(0, 20), 2),
            "mileage_km": mileage_km,
            "bogie_wear_index": round(bogie_wear_index, 4),
            "cleaning_slot": np.random.choice(["Night-A", "Night-B", "No-Clean"]),
            "stabling_position": f"Bay-{np.random.randint(1, 16)}",
            "estimated_shunting_mins": np.random.randint(15, 45),
            "prev_night_shunting_count": prev_night_shunting_count,
            "iot_temp_avg_c": round(np.random.uniform(25.0, 28.5), 2),
            "hvac_alert": int(np.random.choice([0, 1], p=HVAC_ALERT_PROBS)),
            "last_maintenance_date": last_maintenance_date,
            "predicted_failure_risk": 0,
            "manual_override_flag": 0,
            "assigned_status": "Pending"
        }
        data.append(record)

    return pd.DataFrame(data)

def predict_failure_risk(data):
    """Simple failure risk prediction based on multiple factors"""
    risk_scores = []
    
    for _, row in data.iterrows():
        # Base risk from bogie wear
        bogie_risk = row['bogie_wear_index'] * 0.3
        
        # Risk from critical jobs
        job_risk = row['job_critical_count'] * 0.2
        
        # Risk from maintenance delays
        maintenance_risk = 0
        if row['rs_days_from_plan'] <= 0:
            maintenance_risk += 0.3
        if row['sig_days_from_plan'] <= 0:
            maintenance_risk += 0.3
        if row['tel_days_from_plan'] <= 0:
            maintenance_risk += 0.3
        
        # Risk from high mileage
        mileage_risk = min(row['mileage_km'] / 10000, 1) * 0.2
        
        # Risk from temperature issues
        temp_risk = 0
        if row['iot_temp_avg_c'] > 28:
            temp_risk = (row['iot_temp_avg_c'] - 28) / 10 * 0.1
        
        # HVAC alert risk
        hvac_risk = row['hvac_alert'] * 0.1
        
        total_risk = min(bogie_risk + job_risk + maintenance_risk + mileage_risk + temp_risk + hvac_risk, 1.0)
        risk_scores.append(round(total_risk, 4))
    
    return risk_scores

def predict_next_day_mileage(data):
    """Predict next day mileage based on current patterns"""
    mileage_predictions = []
    
    for _, row in data.iterrows():
        # Base mileage with some variation
        base_mileage = np.random.randint(200, 600)
        
        # Adjust based on current mileage (higher current = higher next day)
        mileage_factor = min(row['mileage_km'] / 5000, 1.5)
        
        # Adjust based on depot (some depots have longer routes)
        depot_factor = 1.2 if row['depot'] == "Pettah Depot" else 1.0
        
        predicted_mileage = base_mileage * mileage_factor * depot_factor
        mileage_predictions.append(round(predicted_mileage, 2))
    
    return mileage_predictions

def predict_status(data):
    """Predict train status based on multiple factors"""
    status_predictions = []
    
    for _, row in data.iterrows():
        # Hard constraints - IBL
        if (row['job_critical_count'] > 0 or 
            row['rs_days_from_plan'] <= 0 or 
            row['sig_days_from_plan'] <= 0 or 
            row['tel_days_from_plan'] <= 0):
            status_predictions.append('IBL')
            continue
        
        # Calculate reliability score
        failure_risk = row['predicted_failure_risk']
        reliability_score = 1 - failure_risk
        
        # Calculate passenger experience score
        passenger_score = 100 - (row['hvac_alert'] * 25) - max(0, row['iot_temp_avg_c'] - 28) * 10
        
        # Calculate bogie condition score
        bogie_score = 1 - row['bogie_wear_index']
        
        # Combined score
        combined_score = (reliability_score * 0.4 + 
                         (passenger_score / 100) * 0.3 + 
                         bogie_score * 0.3)
        
        # Determine status based on score
        if combined_score >= 0.7:
            status_predictions.append('Service')
        elif combined_score >= 0.4:
            status_predictions.append('Standby')
        else:
            status_predictions.append('IBL')
    
    return status_predictions

def generate_initial_schedule(data):
    """Generate initial optimized schedule using MetroX_309 logic"""
    global fleet_analytics
    
    # Make predictions
    data['predicted_failure_risk'] = predict_failure_risk(data)
    data['predicted_next_day_mileage'] = predict_next_day_mileage(data)
    data['predicted_status'] = predict_status(data)
    
    # Start with predicted status
    data['final_status'] = data['predicted_status'].copy()
    
    # Apply hard constraints - IBL
    data.loc[
        (data['job_critical_count'] > 0) |
        (data['rs_days_from_plan'] <= 0) |
        (data['sig_days_from_plan'] <= 0) |
        (data['tel_days_from_plan'] <= 0) |
        (data['manual_override_flag'] == 1),
        'final_status'
    ] = 'IBL'

    ibl_trains = data[data['final_status']=='IBL'].copy()
    eligible_trains = data[data['final_status']!='IBL'].copy()

    # Get fleet allocation targets but CAP Service at 14
    if MetroFleetAnalytics:
        fleet_analytics = MetroFleetAnalytics(data)
        fa = fleet_analytics.fleet_allocation_justification()
        TARGET_SERVICE_COUNT = min(fa['min_service_trains'], len(eligible_trains))
    else:
        TARGET_SERVICE_COUNT = min(14, len(eligible_trains))
    
    MAX_SERVICE_TRAINS = 14
    if TARGET_SERVICE_COUNT > MAX_SERVICE_TRAINS:
        TARGET_SERVICE_COUNT = MAX_SERVICE_TRAINS

    # Rank eligible trains by combined score (optimized logic)
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

    # Assign Standby trains (max 4 standby trains)
    MAX_STANDBY_TRAINS = 4
    remaining_after_service = eligible_trains.iloc[TARGET_SERVICE_COUNT:]
    if len(remaining_after_service) > 0:
        # Cap standby trains at maximum of 4
        standby_count = min(len(remaining_after_service), MAX_STANDBY_TRAINS)
        eligible_trains.loc[eligible_trains.index[TARGET_SERVICE_COUNT:TARGET_SERVICE_COUNT + standby_count], 'final_status'] = 'Standby'
        
        # Any remaining trains after service and standby allocation go to IBL
        if len(remaining_after_service) > MAX_STANDBY_TRAINS:
            eligible_trains.loc[eligible_trains.index[TARGET_SERVICE_COUNT + MAX_STANDBY_TRAINS:], 'final_status'] = 'IBL'

    # Combine with original IBL trains
    final_schedule = pd.concat([eligible_trains.drop(columns=['combined_score'], errors='ignore'), ibl_trains])
    final_schedule = final_schedule.sort_values(by='final_status', key=lambda x: x.map({'Service':0,'Standby':1,'IBL':2})).reset_index(drop=True)
    final_schedule['ranking'] = final_schedule.index + 1

    return final_schedule

def generate_alerts(schedule_data):
    """Generate alerts using MetroX_309 analytics"""
    global fleet_analytics
    
    if not MetroFleetAnalytics or schedule_data is None or schedule_data.empty:
        return []
    
    try:
        # Create fleet analytics instance
        if fleet_analytics is None:
            fleet_analytics = MetroFleetAnalytics(schedule_data)
        
        # Get predictive maintenance alerts
        alerts = fleet_analytics.predictive_maintenance_alerts()
        
        # Convert to frontend-friendly format
        formatted_alerts = []
        for alert in alerts:
            for alert_type, severity, value in alert['alerts']:
                formatted_alerts.append({
                    'train_id': alert['train_id'],
                    'depot': alert['depot'],
                    'type': alert_type,
                    'severity': severity,
                    'value': value,
                    'message': f"Train {alert['train_id']} ({alert['depot']}): {alert_type} - {severity} severity (Value: {value})"
                })
        
        return formatted_alerts
    except Exception as e:
        print(f"Error generating alerts: {e}")
        return []

def run_simulation():
    """Run the simulation and generate schedule"""
    global current_schedule, initial_schedule, execution_status, modification_log
    
    try:
        execution_status['is_running'] = True
        execution_status['output'] = []
        execution_status['error'] = None
        execution_status['last_execution'] = datetime.now().isoformat()
        modification_log = []
        
        execution_status['current_step'] = 'Data Simulation'
        execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Starting data simulation...")
        
        # Generate simulated data
        sim_date = datetime.now().date()
        simulated_data = simulate_data_for_day(sim_date)
        
        execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Generated {len(simulated_data)} train records")
        
        # Generate initial schedule
        execution_status['current_step'] = 'Schedule Generation'
        execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] Generating optimized schedule...")
        
        initial_schedule = generate_initial_schedule(simulated_data)
        current_schedule = initial_schedule.copy()
        
        # Show summary
        service_count = len(initial_schedule[initial_schedule['final_status'] == 'Service'])
        standby_count = len(initial_schedule[initial_schedule['final_status'] == 'Standby'])
        ibl_count = len(initial_schedule[initial_schedule['final_status'] == 'IBL'])
        
        execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Schedule generated successfully")
        execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 📊 SUMMARY: {service_count} Service, {standby_count} Standby, {ibl_count} IBL")
        
        # Save to Supabase if available
        if supabase:
            try:
                # Clear existing data
                supabase.table("daily_data").delete().eq("date", sim_date.strftime('%Y-%m-%d')).execute()
                
                # Insert new data
                data_to_insert = simulated_data.to_dict('records')
                supabase.table("daily_data").insert(data_to_insert).execute()
                
                execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 💾 Data saved to Supabase")
            except Exception as e:
                execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Supabase save failed: {str(e)}")
        
        execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] 🎉 Pipeline completed successfully!")
        
    except Exception as e:
        execution_status['error'] = f"Pipeline error: {str(e)}"
        execution_status['output'].append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Pipeline error: {str(e)}")
    finally:
        execution_status['is_running'] = False

def execute_pipeline():
    """Execute the complete pipeline in a separate thread"""
    thread = threading.Thread(target=run_simulation)
    thread.daemon = True
    thread.start()

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current execution status"""
    return jsonify(execution_status)

@app.route('/api/predict', methods=['POST'])
def predict():
    """Start the prediction pipeline"""
    global execution_status
    
    if execution_status['is_running']:
        return jsonify({'error': 'Pipeline is already running'}), 400
    
    execute_pipeline()
    return jsonify({'message': 'Pipeline started'})

@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    """Get current schedule"""
    global current_schedule
    if current_schedule is not None:
        return jsonify(current_schedule.to_dict('records'))
    else:
        return jsonify({'error': 'No schedule available'}), 404

@app.route('/api/modify', methods=['POST'])
def modify_schedule():
    """Modify the schedule"""
    global current_schedule, modification_log
    
    data = request.get_json()
    action = data.get('action')
    train_id = data.get('train_id')
    
    if current_schedule is None:
        return jsonify({'error': 'No schedule available'}), 400
    
    if train_id not in current_schedule['train_id'].values:
        return jsonify({'error': 'Train not found'}), 400
    
    train_row = current_schedule[current_schedule['train_id'] == train_id].iloc[0]
    original_status = train_row['final_status']
    risk = train_row['predicted_failure_risk']
    
    try:
        if action == 'force_service':
            if original_status == 'IBL':
                return jsonify({
                    'error': '❌ SAFETY VIOLATION: Cannot force IBL train to Service',
                    'details': f'Train {train_id} is currently IBL (In Bad Line) due to safety concerns. Forcing to Service would violate safety protocols.',
                    'recommendation': 'Address maintenance issues first before changing status.'
                }), 400
            
            if risk > 0.3:
                return jsonify({
                    'warning': f'⚠️ HIGH RISK WARNING: Failure risk is {risk:.1%}',
                    'details': f'Train {train_id} has a high predicted failure risk of {risk:.1%}. Forcing to Service is not recommended.',
                    'recommendation': 'Consider addressing maintenance issues or use as Standby instead.',
                    'proceed_anyway': True
                })
            
            current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'] = 'Service'
            current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_flag'] = 1
            modification_log.append(f"🚆 {train_id}: {original_status} → Service (Manual override)")
            
            # Generate alerts for this modification
            system_alerts = generate_alerts(current_schedule)
            modification_alerts = [
                f'🚆 Train {train_id} status changed: {original_status} → Service',
                f'⚠️ Manual override flag set for {train_id}',
                f'📊 Failure risk: {risk:.1%}'
            ]
            
            return jsonify({
                'success': True,
                'message': f'✅ Train {train_id} successfully forced to Service',
                'details': f'Status changed from {original_status} to Service. Manual override applied.',
                'new_status': 'Service',
                'modification_log': modification_log,
                'alerts': modification_alerts,
                'system_alerts': system_alerts
            })
            
        elif action == 'force_standby':
            if original_status == 'IBL':
                return jsonify({
                    'error': '❌ SAFETY VIOLATION: Cannot force IBL train to Standby',
                    'details': f'Train {train_id} is currently IBL (In Bad Line) due to safety concerns. Forcing to Standby would violate safety protocols.',
                    'recommendation': 'Address maintenance issues first before changing status.'
                }), 400
            
            current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'] = 'Standby'
            current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_flag'] = 1
            modification_log.append(f"🚆 {train_id}: {original_status} → Standby (Manual override)")
            
            # Generate alerts for this modification
            system_alerts = generate_alerts(current_schedule)
            modification_alerts = [
                f'🚆 Train {train_id} status changed: {original_status} → Standby',
                f'⚠️ Manual override flag set for {train_id}',
                f'📊 Failure risk: {risk:.1%}'
            ]
            
            return jsonify({
                'success': True,
                'message': f'✅ Train {train_id} successfully forced to Standby',
                'details': f'Status changed from {original_status} to Standby. Manual override applied.',
                'new_status': 'Standby',
                'modification_log': modification_log,
                'alerts': modification_alerts,
                'system_alerts': system_alerts
            })
            
        elif action == 'force_ibl':
            current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'] = 'IBL'
            current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_flag'] = 1
            modification_log.append(f"🚆 {train_id}: {original_status} → IBL (Manual override)")
            
            # Generate alerts for this modification
            system_alerts = generate_alerts(current_schedule)
            modification_alerts = [
                f'🚆 Train {train_id} status changed: {original_status} → IBL',
                f'⚠️ Manual override flag set for {train_id}',
                f'🚨 Train {train_id} is now out of service',
                f'📊 Failure risk: {risk:.1%}'
            ]
            
            return jsonify({
                'success': True,
                'message': f'✅ Train {train_id} successfully forced to IBL',
                'details': f'Status changed from {original_status} to IBL. Manual override applied.',
                'new_status': 'IBL',
                'modification_log': modification_log,
                'alerts': modification_alerts,
                'system_alerts': system_alerts
            })
            
        elif action == 'reset':
            predicted_status = train_row['predicted_status']
            current_schedule.loc[current_schedule['train_id'] == train_id, 'final_status'] = predicted_status
            current_schedule.loc[current_schedule['train_id'] == train_id, 'manual_override_flag'] = 0
            modification_log.append(f"🚆 {train_id}: {original_status} → {predicted_status} (Reset)")
            
            # Generate alerts for this modification
            system_alerts = generate_alerts(current_schedule)
            modification_alerts = [
                f'🚆 Train {train_id} status reset: {original_status} → {predicted_status}',
                f'✅ Manual override flag removed for {train_id}',
                f'📊 Failure risk: {risk:.1%}'
            ]
            
            return jsonify({
                'success': True,
                'message': f'✅ Train {train_id} reset to predicted status',
                'details': f'Status changed from {original_status} to {predicted_status}. Manual override removed.',
                'new_status': predicted_status,
                'modification_log': modification_log,
                'alerts': modification_alerts,
                'system_alerts': system_alerts
            })
        
        # Re-rank the schedule
        current_schedule = current_schedule.sort_values(by='final_status', key=lambda x: x.map({'Service': 0, 'Standby': 1, 'IBL': 2})).reset_index(drop=True)
        current_schedule['ranking'] = current_schedule.index + 1
        
    except Exception as e:
        return jsonify({'error': f'Modification failed: {str(e)}'}), 500

@app.route('/api/whatif', methods=['POST'])
def whatif_analysis():
    """Perform what-if analysis"""
    global current_schedule
    
    data = request.get_json()
    scenario = data.get('scenario')
    train_id = data.get('train_id', '')
    
    if current_schedule is None:
        return jsonify({'error': 'No schedule available'}), 400
    
    try:
        if scenario == 'force_service_analysis':
            if train_id not in current_schedule['train_id'].values:
                return jsonify({'error': 'Train not found'}), 400
            
            train_row = current_schedule[current_schedule['train_id'] == train_id].iloc[0]
            current_status = train_row['final_status']
            risk = train_row['predicted_failure_risk']
            
            analysis = {
                'train_id': train_id,
                'current_status': current_status,
                'failure_risk': f"{risk:.1%}",
                'recommendation': 'Can be safely forced to Service' if risk <= 0.3 and current_status != 'IBL' else 'Not recommended for Service',
                'reason': 'High failure risk' if risk > 0.3 else 'IBL train should not be forced to Service' if current_status == 'IBL' else 'Safe to force to Service'
            }
            
        elif scenario == 'simulate_failure':
            if train_id not in current_schedule['train_id'].values:
                return jsonify({'error': 'Train not found'}), 400
            
            train_row = current_schedule[current_schedule['train_id'] == train_id].iloc[0]
            current_status = train_row['final_status']
            standby_count = len(current_schedule[current_schedule['final_status'] == 'Standby'])
            
            analysis = {
                'train_id': train_id,
                'current_status': current_status,
                'service_impact': 'Requires immediate standby deployment' if current_status == 'Service' else 'Minimal service impact',
                'available_standby': standby_count,
                'critical': standby_count == 0 and current_status == 'Service'
            }
            
        elif scenario == 'maintenance_delay':
            high_risk = len(current_schedule[current_schedule['predicted_failure_risk'] > 0.25])
            analysis = {
                'high_risk_trains': high_risk,
                'impact': f"{high_risk} trains would become critical" if high_risk > 0 else "No high-risk trains affected"
            }
            
        elif scenario == 'headway_analysis':
            new_headway = data.get('headway', 10)
            total_fleet_size = 25
            service_hours = 16.5
            min_standby = 3
            avg_trip_duration = 2.0
            
            trains_needed = (avg_trip_duration * 60) / new_headway
            total_needed = trains_needed + min_standby
            
            analysis = {
                'new_headway': new_headway,
                'trains_needed': trains_needed,
                'total_needed': total_needed,
                'feasible': total_needed <= total_fleet_size,
                'shortage': max(0, total_needed - total_fleet_size)
            }
            
        else:
            return jsonify({'error': 'Invalid scenario'}), 400
        
        return jsonify(analysis)
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/data/simulated', methods=['GET'])
def get_simulated_data():
    """Get simulated today data"""
    global current_schedule
    if current_schedule is not None:
        return jsonify(current_schedule.to_dict('records'))
    else:
        return jsonify({'error': 'No simulated data available'}), 404

@app.route('/api/data/predictions', methods=['GET'])
def get_predictions():
    """Get next day predictions"""
    global current_schedule
    if current_schedule is not None:
        return jsonify(current_schedule.to_dict('records'))
    else:
        return jsonify({'error': 'No prediction data available'}), 404

@app.route('/api/data/history', methods=['GET'])
def get_history():
    """Get historical data"""
    return jsonify({'error': 'Historical data not available in integrated mode'}), 404

@app.route('/api/modification-log', methods=['GET'])
def get_modification_log():
    """Get modification log"""
    global modification_log
    return jsonify({'modification_log': modification_log})

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get current alerts"""
    global current_schedule
    if current_schedule is not None:
        alerts = generate_alerts(current_schedule)
        return jsonify({'alerts': alerts})
    else:
        return jsonify({'alerts': []})

@app.route('/api/fleet-analytics', methods=['GET'])
def get_fleet_analytics():
    """Get KMRL Fleet Analytics Report"""
    global current_schedule, fleet_analytics
    
    if current_schedule is None or not MetroFleetAnalytics:
        return jsonify({'error': 'No schedule data available or analytics not loaded'}), 404
    
    try:
        # Create fleet analytics instance if not exists
        if fleet_analytics is None:
            fleet_analytics = MetroFleetAnalytics(current_schedule)
        
        # Generate comprehensive report
        report = fleet_analytics.generate_kmrl_report()
        return jsonify({'report': report})
    except Exception as e:
        return jsonify({'error': f'Failed to generate analytics report: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Starting MetroX Scheduler Backend...")
    print("✅ All logic integrated - no external dependencies")
    app.run(debug=True, host='0.0.0.0', port=5000)