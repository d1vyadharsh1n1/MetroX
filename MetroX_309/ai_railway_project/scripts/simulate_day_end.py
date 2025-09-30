import pandas as pd
import numpy as np
from datetime import date, timedelta
import os
import logging
from supabase import create_client
from dotenv import load_dotenv

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ----------------------------
# Supabase Client Setup
# ----------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE1_URL")
SUPABASE_KEY = os.getenv("SUPABASE1_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ----------------------------
# Helpers
# ----------------------------
def get_train_ids():
    return [f"KM-T{101 + i}" for i in range(25)]

def simulate_data_for_day(sim_date: date, prev_day_df: pd.DataFrame = None):
    """
    Simulates daily train data. If prev_day_df is provided, some metrics
    are updated based on previous day's values.
    """
    train_ids = get_train_ids()
    data = []

    CRITICAL_JOB_PROB = [0.98, 0.015, 0.005]
    HVAC_ALERT_PROBS = [0.85, 0.15]

    for train_id in train_ids:
        if prev_day_df is not None and train_id in prev_day_df['train_id'].values:
            prev_row = prev_day_df[prev_day_df['train_id'] == train_id].iloc[0]
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
            "manual_override_flag": 0,  # always 0 initially
            "assigned_status": "Pending"
        }

        data.append(record)

    return pd.DataFrame(data)

# ----------------------------
# Push functions
# ----------------------------
def push_daily_data(df: pd.DataFrame):
    """Replace existing daily_data with new 25 rows."""
    if df.empty:
        logging.warning("No data to push to daily_data.")
        return

    sim_date = df['date'].iloc[0]

    try:
        supabase.table("daily_data").delete().eq("date", sim_date).execute()
        logging.info(f"Deleted existing rows for date {sim_date} in daily_data.")
    except Exception as e:
        logging.error(f"Failed to delete rows in daily_data: {e}")

    try:
        for _, row in df.iterrows():
            supabase.table("daily_data").insert(row.to_dict()).execute()
        logging.info(f"Pushed {len(df)} rows to daily_data.")
    except Exception as e:
        logging.error(f"Failed to push rows to daily_data: {e}")

def push_daily_history(df: pd.DataFrame):
    """Append all simulated rows to daily_data_history."""
    if df.empty:
        logging.warning("No data to push to daily_data_history.")
        return

    try:
        for _, row in df.iterrows():
            supabase.table("daily_data_history").insert(row.to_dict()).execute()
        logging.info(f"Appended {len(df)} rows to daily_data_history.")
    except Exception as e:
        logging.error(f"Failed to push rows to daily_data_history: {e}")

# ----------------------------
# Main
# ----------------------------
def main():
    sim_date = date.today()

    # Fetch previous day's data
    try:
        prev_response = supabase.table("daily_data").select("*") \
            .eq("date", (sim_date - timedelta(days=1)).strftime('%Y-%m-%d')).execute()
        prev_df = pd.DataFrame(prev_response.data) if prev_response.data else None
        logging.info(f"Fetched {len(prev_df) if prev_df is not None else 0} rows from previous day.")
    except Exception as e:
        logging.warning(f"Could not fetch previous day data: {e}")
        prev_df = None

    # Simulate today's data
    df_sim = simulate_data_for_day(sim_date, prev_day_df=prev_df)

    # Push to tables
    push_daily_data(df_sim)       # replace 25 rows in daily_data
    push_daily_history(df_sim)    # append to daily_data_history

if __name__ == "__main__":
    main()