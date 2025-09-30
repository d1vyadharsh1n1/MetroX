import pandas as pd
import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_supabase_client():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Supabase credentials must be in the .env file.")
    return create_client(url, key)

def main():
    logging.info("Starting database setup process...")
    try:
        supabase = get_supabase_client()
        table_name = "history"
        csv_path = "data/kmrl_40_trains_history.csv"
        
        logging.info(f"Reading data from {csv_path}...")
        if not os.path.exists(csv_path):
            logging.error(f"Data file not found at {csv_path}. Please make sure it's in the 'data' directory.")
            return

        df = pd.read_csv(csv_path)
        logging.info(f"Loaded {len(df)} rows and {len(df.columns)} columns from CSV.")

        # IMPORTANT: Create the unique dayid for the initial dataset
        df['dayid'] = df.apply(lambda row: f"{row['date']}-{row['train_id']}", axis=1)
        
        # Ensure column order matches the schema and handle potential missing columns
        schema_cols = [
            'dayid', 'date', 'train_id', 'depot', 'rs_days_from_plan', 'sig_days_from_plan',
            'tel_days_from_plan', 'job_open_count', 'job_critical_count', 'branding_req_hours',
            'branding_alloc_hours', 'mileage_km', 'bogie_wear_index', 'cleaning_slot',
            'stabling_position', 'estimated_shunting_mins', 'prev_night_shunting_count',
            'iot_temp_avg_c', 'hvac_alert', 'last_maintenance_date', 'predicted_failure_risk',
            'manual_override_flag', 'assigned_status'
        ]
        df = df[schema_cols]
        
        data_to_insert = df.to_dict(orient='records')
        
        logging.info(f"Uploading {len(data_to_insert)} records to Supabase table '{table_name}'...")
        response = supabase.table(table_name).insert(data_to_insert).execute()

        if len(response.data) > 0:
            logging.info(f"Successfully uploaded {len(response.data)} records.")
        else:
             logging.error(f"Failed to upload data. Error: {response.get('error')}")

    except Exception as e:
        logging.error(f"An error occurred during database setup: {e}", exc_info=True)

if __name__ == "__main__":
    main()

