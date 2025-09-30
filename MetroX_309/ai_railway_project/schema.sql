-- Drop the table if it exists to start fresh (optional, for testing)
DROP TABLE IF EXISTS public.history;

-- Create the main table for historical train data
CREATE TABLE public.history (
-- New, more robust Primary Key: YYYY-MM-DD-TRAIN_ID
dayid TEXT PRIMARY KEY,
date DATE NOT NULL,
train_id TEXT NOT NULL,
depot TEXT,
rs_days_from_plan INTEGER,
sig_days_from_plan INTEGER,
tel_days_from_plan INTEGER,
job_open_count INTEGER,
job_critical_count INTEGER,
branding_req_hours REAL,
branding_alloc_hours REAL,
mileage_km INTEGER,
bogie_wear_index REAL,
cleaning_slot TEXT,
stabling_position TEXT,
estimated_shunting_mins INTEGER,
prev_night_shunting_count INTEGER,
iot_temp_avg_c REAL,
hvac_alert INTEGER,
last_maintenance_date DATE,
predicted_failure_risk REAL,
manual_override_flag INTEGER,
assigned_status TEXT
);

-- Add comments for clarity
COMMENT ON COLUMN public.history.dayid IS 'Unique identifier for a train on a specific day, format YYYY-MM-DD-TRAIN_ID';
COMMENT ON COLUMN public.history.bogie_wear_index IS 'A calculated index representing wear on the bogie components.';
COMMENT ON COLUMN public.history.predicted_failure_risk IS 'The ML model''s predicted risk of failure for the next day.';
