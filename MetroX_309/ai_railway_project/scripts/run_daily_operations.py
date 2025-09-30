import subprocess
import sys
import os
import logging
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import date

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "history"

def run_script(script_name):
    """Runs a python script as a subprocess and checks for errors."""
    logging.info(f"--- Running script: {script_name} ---")
    try:
        process = subprocess.run([sys.executable, script_name], check=True, capture_output=True, text=True)
        logging.info(f"Output from {script_name}:\n{process.stdout}")
        if process.stderr:
            # Some scripts might print to stderr without it being a true error, so we log as warning.
            logging.warning(f"Standard Error from {script_name}:\n{process.stderr}")
        logging.info(f"--- Finished script: {script_name} ---")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"!!! FAILED to run script: {script_name} !!!")
        logging.error(f"Return code: {e.returncode}")
        logging.error(f"Output:\n{e.stdout}")
        logging.error(f"Error:\n{e.stderr}")
        return False

def update_historical_data():
    """
    Ensures the historical table is updated with the latest daily simulation.
    It deletes any existing records for the current day before inserting new ones.
    """
    logging.info("--- Starting Supabase data update process ---")
    simulated_data_path = "data/simulated_today.csv"
    
    if not os.path.exists(simulated_data_path):
        logging.error(f"Simulated data file not found at {simulated_data_path}. Cannot update history.")
        return

    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # --- NEW DELETE-THEN-INSERT LOGIC ---
        today_str = date.today().strftime('%Y-%m-%d')
        logging.info(f"Checking for and removing any existing records for date: {today_str}")
        
        # Delete any records that match today's date to prevent duplicates
        delete_response = supabase.table(TABLE_NAME).delete().eq('date', today_str).execute()
        
        if delete_response.data:
            logging.warning(f"Successfully deleted {len(delete_response.data)} old records for {today_str} to make way for the new ones.")
        else:
            logging.info(f"No existing records found for {today_str}. Proceeding with insert.")
        # --- END OF NEW LOGIC ---

        # Now, proceed with inserting the new data
        df = pd.read_csv(simulated_data_path)
        predictions_df = pd.read_csv("data/next_day_predictions.csv")
        
        # Merge predictions back into the daily data before uploading
        status_map = predictions_df.set_index('train_id')['predicted_status'].to_dict()
        risk_map = predictions_df.set_index('train_id')['predicted_failure_risk'].to_dict()
        
        df['assigned_status'] = df['train_id'].map(status_map)
        df['predicted_failure_risk'] = df['train_id'].map(risk_map)

        data_to_insert = df.to_dict(orient='records')
        
        logging.info(f"Inserting {len(data_to_insert)} new records for {today_str}...")
        insert_response = supabase.table(TABLE_NAME).insert(data_to_insert).execute()
        
        if len(insert_response.data) > 0:
            logging.info(f"Successfully inserted {len(insert_response.data)} new records into the '{TABLE_NAME}' table.")
        else:
            logging.error(f"Failed to insert new data. Supabase response: {insert_response.get('error') or insert_response}")
            
    except Exception as e:
        logging.error(f"An error occurred during the Supabase update process: {e}", exc_info=True)

def main():
    """Orchestrates the daily simulation, prediction, and database update workflow."""
    logging.info("====== STARTING DAILY OPERATIONS WORKFLOW ======")
    
    # Step 1: Simulate the end of the current day's operations.
    if not run_script("scripts/simulate_day_end.py"):
        logging.critical("Daily simulation failed. Halting workflow.")
        return

    # Step 2: Run predictions on the simulated data to get the next day's schedule.
    if not run_script("scripts/predict_next_day_schedule.py"):
        logging.critical("Prediction for next day failed. Halting workflow.")
        return

    # Step 3: Update the historical database with the results of today's simulation.
    update_historical_data()

    logging.info("====== DAILY OPERATIONS WORKFLOW COMPLETED ======")
    logging.info("The Supabase 'history' table has been updated with the latest data for today.")
    logging.info("You can retrain the models with the new data by running 'python scripts/train_models.py' periodically.")

if __name__ == "__main__":
    main()

