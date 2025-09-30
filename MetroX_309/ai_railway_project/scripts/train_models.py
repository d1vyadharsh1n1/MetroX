import os
import pandas as pd
import numpy as np # IMPORT numpy for square root
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.preprocessing import LabelEncoder

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "history"
MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)

def get_supabase_client() -> Client:
    """Initializes and returns the Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials must be in the .env file.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_data(supabase: Client) -> pd.DataFrame:
    """Fetches all data from the history table."""
    logging.info(f"Fetching data from '{TABLE_NAME}'...")
    try:
        response = supabase.table(TABLE_NAME).select("*").execute()
        df = pd.DataFrame(response.data)
        logging.info(f"Successfully fetched {len(df)} records.")
        return df
    except Exception as e:
        logging.error(f"Failed to fetch data: {e}")
        return pd.DataFrame()

def preprocess_data(df: pd.DataFrame):
    """Preprocesses the data for model training."""
    logging.info("Preprocessing data...")
    df.drop(columns=['id', 'created_at', 'dayid', 'train_id', 'date', 'last_maintenance_date'], inplace=True, errors='ignore')
    
    df = pd.get_dummies(df, columns=['depot', 'cleaning_slot', 'stabling_position'], drop_first=True)
    
    if 'assigned_status' in df.columns:
        le = LabelEncoder()
        df['assigned_status_encoded'] = le.fit_transform(df['assigned_status'])
        joblib.dump(le, os.path.join(MODELS_DIR, 'status_label_encoder.pkl'))
        df.drop('assigned_status', axis=1, inplace=True)

    df.fillna(df.median(numeric_only=True), inplace=True)
            
    return df

def train_status_prediction_model(df: pd.DataFrame):
    """Trains a model to predict the 'assigned_status'."""
    logging.info("Training 'Assigned Status Prediction' model...")
    target = 'assigned_status_encoded'
    if target not in df.columns:
        logging.error(f"Target column '{target}' not found. Aborting status model training.")
        return

    features = [col for col in df.columns if col != target and 'failure_risk' not in col]
    X = df[features]
    y = df[target]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42, oob_score=True)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    logging.info(f"Status Prediction Model Accuracy: {accuracy:.4f}")
    
    joblib.dump(model, os.path.join(MODELS_DIR, 'assigned_status_classifier.pkl'))
    logging.info("Saved status prediction model.")

def train_failure_risk_model(df: pd.DataFrame):
    """Trains a model to predict 'predicted_failure_risk'."""
    logging.info("Training 'Failure Risk Forecasting' model...")
    target = 'predicted_failure_risk'
    if target not in df.columns:
        logging.error(f"Target column '{target}' not found. Aborting failure risk model training.")
        return
        
    features = [col for col in df.columns if col != target and 'status' not in col]
    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    # --- FIX APPLIED HERE ---
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse) 
    # --- END OF FIX ---
    logging.info(f"Failure Risk Model RMSE: {rmse:.4f}")
    
    joblib.dump(model, os.path.join(MODELS_DIR, 'failure_risk_regressor.pkl'))
    logging.info("Saved failure risk model.")

def train_mileage_wear_model(df: pd.DataFrame):
    """Trains a model to predict mileage."""
    logging.info("Training 'Mileage Forecasting' model...")
    target = 'mileage_km'
    if target not in df.columns:
        logging.error(f"Target column '{target}' not found. Aborting mileage model training.")
        return
        
    features = [col for col in df.columns if col != target and 'wear' not in col]
    
    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    # --- FIX APPLIED HERE ---
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    # --- END OF FIX ---
    logging.info(f"Mileage Forecasting Model RMSE: {rmse:.4f}")
    
    joblib.dump(model, os.path.join(MODELS_DIR, 'mileage_regressor.pkl'))
    logging.info("Saved mileage forecasting model.")

def main():
    """Main function to fetch data and train all models."""
    logging.info("Starting model training process...")
    try:
        supabase = get_supabase_client()
        df = fetch_data(supabase)
        
        if df.empty:
            logging.error("No data fetched. Aborting training.")
            return
            
        processed_df = preprocess_data(df.copy())
        
        train_status_prediction_model(processed_df.copy())
        train_failure_risk_model(processed_df.copy())
        train_mileage_wear_model(processed_df.copy())
        
        logging.info("All models trained successfully.")
    except Exception as e:
        logging.error(f"Model training script failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()

