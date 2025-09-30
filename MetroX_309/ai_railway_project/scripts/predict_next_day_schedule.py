import pandas as pd
import joblib
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')



MODELS_DIR = "ai_railway_project/models"
INPUT_CSV = "ai_railway_project/data/simulated_today.csv"



def load_models():
    """Loads all trained models from the models directory."""
    logging.info("Loading trained models...")
    models = {}
    try:
        models['status_classifier'] = joblib.load(os.path.join(MODELS_DIR, 'assigned_status_classifier.pkl'))
        models['failure_regressor'] = joblib.load(os.path.join(MODELS_DIR, 'failure_risk_regressor.pkl'))
        models['mileage_regressor'] = joblib.load(os.path.join(MODELS_DIR, 'mileage_regressor.pkl'))
        models['status_encoder'] = joblib.load(os.path.join(MODELS_DIR, 'status_label_encoder.pkl'))
        logging.info("All models loaded successfully.")
        return models
    except FileNotFoundError as e:
        logging.error(f"Error loading model: {e}. Make sure 'train_models.py' has been run successfully.")
        return None

def preprocess_for_prediction(df: pd.DataFrame, historical_columns):
    """Prepares new data for prediction, ensuring columns match training data."""
    logging.info("Preprocessing data for prediction...")
    df_processed = df.copy()
    
    train_ids = df_processed['train_id']
    
    df_processed.drop(columns=['dayid', 'train_id', 'date', 'last_maintenance_date', 'assigned_status'], inplace=True, errors='ignore')

    df_processed = pd.get_dummies(df_processed, columns=['depot', 'cleaning_slot', 'stabling_position'], drop_first=True)
    
    df_processed = df_processed.reindex(columns=historical_columns, fill_value=0)
    
    return df_processed.fillna(0), train_ids


def make_predictions(models, data: pd.DataFrame):
    """Makes predictions using the loaded models."""
    if models is None or data.empty:
        logging.error("Models not loaded or data is empty. Aborting prediction.")
        return None
    
    logging.info("Making predictions on new data...")
    
    status_features = models['status_classifier'].feature_names_in_
    failure_features = models['failure_regressor'].feature_names_in_
    mileage_features = models['mileage_regressor'].feature_names_in_

    all_features = list(set(list(status_features)) | set(list(failure_features)) | set(list(mileage_features)))
    
    processed_data, train_ids = preprocess_for_prediction(data.copy(), all_features)

    predictions = pd.DataFrame({'train_id': train_ids})

    # 1. Assigned Status Prediction
    status_pred_encoded = models['status_classifier'].predict(processed_data[status_features])
    predictions['predicted_status'] = models['status_encoder'].inverse_transform(status_pred_encoded)
    
    # 2. Failure Risk Forecasting
    predictions['predicted_failure_risk'] = models['failure_regressor'].predict(processed_data[failure_features])
    
    # 3. Mileage Forecasting
    predictions['predicted_next_day_mileage'] = models['mileage_regressor'].predict(processed_data[mileage_features])
    
    predictions['predicted_failure_risk'] = predictions['predicted_failure_risk'].round(4)
    predictions['predicted_next_day_mileage'] = predictions['predicted_next_day_mileage'].round(2)

    logging.info("Predictions generated successfully.")
    return predictions
def get_reasoning(df):
    """
    Generates a list of reasons for a train's final status.
    """
    reasons = []
    for _, train in df.iterrows():
        reason_list = []
        if train['predicted_status'] == 'IBL':
            reason_list.append("ML model predicted IBL due to low reliability.")
        
        if train['final_status'] == 'IBL' and train['predicted_status'] != 'IBL':
            reason_list.append("Status was changed to 'IBL' by rule-based logic.")
            if train['job_critical_count'] > 0:
                reason_list.append(f"Reason: Critical job card ({train['job_critical_count']} open).")
            if train['rs_days_from_plan'] <= 0:
                reason_list.append(f"Reason: Expired Rolling-Stock certificate ({train['rs_days_from_plan']} days).")
            if train['sig_days_from_plan'] <= 0:
                reason_list.append(f"Reason: Expired Signalling certificate ({train['sig_days_from_plan']} days).")
            if train['tel_days_from_plan'] <= 0:
                reason_list.append(f"Reason: Expired Telecom certificate ({train['tel_days_from_plan']} days).")
        
        reasons.append({
            'train_id': train['train_id'],
            'final_status': train['final_status'],
            'reasoning': " ".join(reason_list) if reason_list else "No specific reason identified. Status is as predicted by ML model."
        })
    return reasons

def main():
    """Main function to load data, models, and generate a ranked schedule."""
    if not os.path.exists(INPUT_CSV):
        logging.error(f"Input file not found: {INPUT_CSV}. Run 'simulate_day_end.py' first.")
        return

    simulated_data = pd.read_csv(INPUT_CSV)
    models = load_models()
    
    if models:
        final_predictions = make_predictions(models, simulated_data)
        if final_predictions is not None:
            
            # --- NEW SORTING LOGIC ADDED HERE ---
            logging.info("Sorting predictions into a ranked operational list...")
            # Define the custom order for sorting
            status_priority = {
                "Service": 0,
                "Standby": 1,
                "IBL": 2
            }
            # Create a temporary column for sorting based on the priority map
            final_predictions['sort_priority'] = final_predictions['predicted_status'].map(status_priority)
            
            # Sort by the priority column first, then by failure risk
            ranked_schedule = final_predictions.sort_values(
                by=['sort_priority', 'predicted_failure_risk'],
                ascending=[True, True]
            ).drop(columns=['sort_priority']) # Remove the temporary column
            # --- END OF NEW SORTING LOGIC ---

            print("\n--- Next Day Operations Ranked Schedule ---")
            print(ranked_schedule.to_string()) # Use to_string() to ensure all rows are printed
            print("-------------------------------------------\n")
            
            output_path = "ai_railway_project/data/next_day_predictions1.csv"
            ranked_schedule.to_csv(output_path, index=False)
            logging.info(f"Saved ranked schedule to {output_path}")

if __name__ == "__main__":
    main()

