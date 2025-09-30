# MetroX Scheduler - Full Stack Application

A comprehensive full-stack application for AI-powered metro train scheduling and optimization, built with Flask backend and React frontend.

## 🚇 Overview

The MetroX Scheduler system uses advanced machine learning models to optimize train scheduling, predict failure risks, and ensure efficient metro operations. The system processes daily train data, applies predictive analytics, and generates optimized schedules for the next day's operations.

## 🏗️ Architecture

### Backend (Flask)
- **Location**: `backend/`
- **Port**: 5000
- **Framework**: Flask with CORS support
- **Scripts Integration**: Executes `simulate_day_end.py` and `predict_schedule_optimised.py`

### Frontend (React)
- **Location**: `frontend/`
- **Port**: 3000
- **Framework**: React with Vite
- **UI Library**: Ant Design

### Python Scripts
- **Location**: `MetroX_309/ai_railway_project/scripts/`
- **Main Scripts**:
  - `simulate_day_end.py`: Simulates daily train data
  - `predict_schedule_optimised.py`: Generates optimized schedules using ML models

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000

## 📱 Features

### 1. Home Dashboard
- System overview and quick access to all features
- Fleet statistics and health indicators

### 2. Scheduler
- **Run Prediction**: Execute the complete scheduling pipeline
- **Real-time Status**: Monitor script execution progress
- **Schedule Display**: View ranked train schedules with status indicators
- **Execution Logs**: See detailed output from Python scripts

### 3. Dashboard
- **Fleet Overview**: Service, Standby, and IBL train counts
- **Risk Analysis**: High, medium, and low-risk train categorization
- **Maintenance Alerts**: Critical maintenance requirements
- **System Status**: Pipeline and ML model status

### 4. Execution Logs
- **Real-time Monitoring**: Live updates during script execution
- **Timeline View**: Chronological execution steps
- **Raw Output**: Complete terminal output from Python scripts
- **System Information**: Script paths and configuration

### 5. Data Viewer
- **Simulated Data**: Current day's simulated train data
- **Predictions**: ML-generated schedule predictions
- **Historical Data**: Past train performance data
- **Data Statistics**: Summary of all datasets

## 🔧 API Endpoints

### Status & Control
- `GET /api/status` - Get current execution status
- `POST /api/predict` - Start prediction pipeline
- `GET /api/health` - Health check

### Data Access
- `GET /api/data/simulated` - Get simulated today data
- `GET /api/data/predictions` - Get next day predictions
- `GET /api/data/history` - Get historical data

## 📊 Data Flow

1. **Simulation Phase**: `simulate_day_end.py` generates daily train data
2. **Prediction Phase**: `predict_schedule_optimised.py` applies ML models
3. **Optimization**: Interactive schedule modification and validation
4. **Output**: Ranked schedule with status assignments

## 🎯 Key Features

### Real-time Execution
- Live status updates during script execution
- Progress indicators and error handling
- Automatic data refresh after completion

### Interactive Scheduling
- Manual override capabilities
- Safety checks and validation
- What-if scenario analysis

### Comprehensive Monitoring
- Fleet health indicators
- Risk assessment and alerts
- Maintenance scheduling

### Data Visualization
- Interactive tables and charts
- Status color coding
- Responsive design

## 🛠️ Development

### Backend Development
```bash
cd backend
python app.py  # Development server with auto-reload
```

### Frontend Development
```bash
cd frontend
npm run dev    # Development server with hot reload
```

### Script Integration
The backend automatically:
- Changes to the correct working directory
- Executes Python scripts with proper error handling
- Captures and streams output
- Handles timeouts and failures

## 📁 Project Structure

```
MetroX_309/
├── backend/
│   ├── app.py              # Flask application
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/         # React components
│   │   ├── App.jsx        # Main application
│   │   └── main.jsx       # Entry point
│   ├── package.json       # Node dependencies
│   └── vite.config.js     # Vite configuration
├── MetroX_309/
│   └── ai_railway_project/
│       ├── scripts/       # Python scripts
│       └── data/          # Data files
└── README.md
```

## 🔍 Troubleshooting

### Common Issues
1. **Scripts not found**: Ensure Python scripts are in the correct directory
2. **Port conflicts**: Change ports in `vite.config.js` and `app.py`
3. **CORS errors**: Backend includes CORS support for frontend communication
4. **Data not loading**: Check if Python scripts have generated data files

### Logs and Debugging
- Check browser console for frontend errors
- Monitor backend terminal output
- Use the Logs page for detailed execution information

## 🚀 Deployment

### Production Build
```bash
# Frontend
cd frontend
npm run build

# Backend
cd backend
# Use production WSGI server like Gunicorn
```

### Environment Variables
- Configured Supabase credentials in `.env` file

## 📈 Future Enhancements

- Real-time data streaming
- Advanced analytics dashboard
- Mobile-responsive design
- Export capabilities
- User authentication
- Multi-tenant support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request


