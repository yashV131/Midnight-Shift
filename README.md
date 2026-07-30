# ATLAS

**ATLAS** is an intelligent productivity and security dashboard designed to help users maintain focus and security during long work sessions. It combines eye-tracking technology, real-time screen monitoring, and smart device locking to provide comprehensive analytics on productivity, distractions, and user presence.

## Overview

ATLAS monitors your work environment in real-time to:
- **Track Eye Engagement**: Detect eye gaze patterns and attention levels using computer vision
- **Monitor Screen Activity**: Identify active applications and distractions in real-time
- **Auto-Lock Mechanism**: Automatically lock your device when you look away or are inactive
- **Productivity Analytics**: Generate detailed reports on work sessions, distractions, and focus time
- **Real-time Dashboard**: Visualize all metrics and stats through a modern, intuitive interface

## Key Features

### Eye Tracking
- Real-time eye gaze detection using webcam and face recognition
- Detects when user looks away from screen (attention loss)
- Tracks blink patterns and fatigue indicators
- Uses dlib and face-recognition libraries for accurate detection

### Screen Monitoring
- Captures active window titles and application usage
- Identifies distracting applications and websites
- Monitors screen activity patterns
- Records session duration and activity timestamps

### Auto-Lock Security
- Automatically locks screen when user is away or looking away
- Subprocess-based lock mechanism for quick activation
- Prevents unauthorized access during unattended sessions
- Configurable lock triggers

### Analytics & Reporting
- Tracks distraction categories and frequency
- Generates daily productivity reports
- Session-based analytics with detailed breakdowns
- Real-time statistics dashboard
- Historical data storage in persistent database

### Modern Dashboard UI
- React + TypeScript frontend with Vite
- Beautiful, responsive design using Shadcn/Radix UI components
- Retro-styled aesthetic with modern UX
- Real-time data visualization with Recharts
- Dark theme optimized for extended work sessions

## Tech Stack

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: Shadcn/Radix UI (comprehensive component library)
- **Charting**: Recharts for data visualization
- **State Management**: React Hooks
- **Forms**: React Hook Form

### Backend
- **Framework**: Flask + Flask-CORS
- **Language**: Python 3.8+
- **Computer Vision**: OpenCV, dlib, face-recognition
- **Database**: Custom SQLite-based DatabaseManager
- **Object Detection**: YOLOv8 (Ultralytics)
- **System Integration**: psutil, win10toast for notifications

## Prerequisites

- **Python**: 3.8 or higher (up to 3.13)
- **Node.js**: Latest LTS version (for frontend)
- **Webcam**: Required for eye tracking functionality
- **Windows OS**: Optimized for Windows 10/11 (uses win10toast for notifications)

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yashV131/Midnight-Shift.git
cd Midnight-Shift
```

### 2. Backend Setup

Install Python dependencies:
```bash
pip install -r requirements.txt
```

This installs:
- Flask and Flask-CORS (web framework)
- OpenCV (computer vision)
- dlib & face-recognition (facial recognition)
- YOLOv8 (object detection)
- psutil (system monitoring)
- win10toast (Windows notifications)

### 3. Frontend Setup

Install Node.js dependencies and start dev server:
```bash
npm install
npm run dev
```

### 4. Start the Backend

In a separate terminal:
```bash
python backend/app.py
```

The backend will:
- Start Flask server on `http://127.0.0.1:5000`
- Automatically launch screen monitoring thread
- Activate eye tracking via webcam
- Start lock mechanism subprocess

### 5. Access the Dashboard

Open your browser and navigate to `http://localhost:5173` (Vite dev server) to access the ATLAS dashboard.

## How It Works

### Monitoring Flow

1. **Session Initialization**: When you start monitoring, a new session is created and stored in the database
2. **Screen Monitoring**: A dedicated thread monitors active windows and captures distraction data
3. **Eye Tracking**: Eye tracking runs in parallel, detecting gaze and attention patterns
4. **Lock Mechanism**: A subprocess monitors for lock triggers (away/looking away conditions)
5. **Data Collection**: All metrics are aggregated and stored in the database
6. **Real-time Display**: Frontend polls the backend API for latest stats and updates the dashboard

### Key Components

- **`backend/app.py`**: Main Flask application and MonitoringManager
- **`backend/read_screen.py`**: ScreenMonitor class for capturing active windows
- **`backend/eyetracking.py`**: EyeTracker class for real-time eye gaze detection
- **`backend/lockMechanism.py`**: Auto-lock subprocess
- **`backend/database.py`**: DatabaseManager for persistent data storage
- **`src/App.tsx`**: Main React dashboard component
- **`src/components/ui/`**: Reusable UI component library

## Usage

1. Start the backend and frontend as described above
2. Click "Start Monitoring" on the dashboard
3. Work as normal - the system will track:
   - Eye gaze and attention
   - Active applications
   - Distraction patterns
   - Session duration
4. View real-time analytics on the dashboard
5. Click "Stop Monitoring" to end the session

## DEMO

[![Watch the video](https://img.youtube.com/vi/O2-cWS0dveY/maxresdefault.jpg)](https://youtu.be/O2-cWS0dveY)

Watch the demo video above for a detailed analysis and walkthrough of ATLAS features.

## Project Structure

```
├── backend/                 # Python Flask backend
│   ├── app.py              # Main Flask app and MonitoringManager
│   ├── database.py         # Database operations
│   ├── read_screen.py      # Screen monitoring
│   ├── eyetracking.py      # Eye tracking module
│   ├── lockMechanism.py    # Auto-lock functionality
│   └── requirements.txt    # Python dependencies
├── src/                    # React TypeScript frontend
│   ├── App.tsx            # Main dashboard component
│   ├── components/        # Reusable components
│   │   ├── ui/           # Shadcn/Radix UI components
│   │   └── figma/        # Custom components
│   ├── guidelines/        # Design guidelines
│   └── styles/           # Global styles
├── package.json           # Node.js dependencies
├── vite.config.ts        # Vite configuration
└── README.md             # This file
```

## Future Improvements

- Cross-platform support (macOS, Linux)
- Advanced ML models for distraction prediction
- Customizable distraction categories
- Export reports to PDF
- Integration with productivity tools
- Offline mode support
- Mobile app companion

## Notes

- Requires webcam for full functionality
- Best used on dedicated work machine for privacy
- Sensitive to lighting conditions for eye tracking accuracy
- Windows 10/11 optimized (uses platform-specific features)

## License

[Add license information if applicable]

## Support

For issues or questions, please open an issue on the GitHub repository.
