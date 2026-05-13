# app.py
import threading
import subprocess
import os
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from win10toast import ToastNotifier

from backend.database import DatabaseManager
from backend.read_screen import ScreenMonitor
from backend.eyetracking import EyeTracker

class MonitoringManager:
    """Manages the lifecycle of all monitoring tasks."""
    def __init__(self, db_manager):
        self.db = db_manager
        self.is_monitoring = False
        self.session_id = None
        self.stop_event = None
        self.threads = {}
        self.processes = {}
        self.toaster = ToastNotifier()

    def start(self):
        if self.is_monitoring:
            return False, "Monitoring is already active."

        self.is_monitoring = True
        self.session_id = self.db.start_session()
        self.stop_event = threading.Event()

        screen_monitor = ScreenMonitor(self.session_id, self.stop_event, self.db)
        self.threads['screen'] = threading.Thread(target=screen_monitor.start_monitoring, daemon=True)

        eye_tracker = EyeTracker(self.stop_event)
        self.threads['eye'] = threading.Thread(target=eye_tracker.start_tracking, daemon=True)
        
        self.processes['lock'] = subprocess.Popen(['python', 'lockMechanism.py'])

        for thread in self.threads.values():
            thread.start()
        
        self.toaster.show_toast("MidnightShift", "Monitoring Started", threaded=True)
        print(f"Monitoring started for session: {self.session_id}")
        return True, "Monitoring started successfully."

    def stop(self):
        if not self.is_monitoring:
            return False, "Monitoring is not active."

        if self.stop_event:
            self.stop_event.set()

        for process in self.processes.values():
            if process.poll() is None:
                process.terminate()
        self.processes.clear()

        for thread in self.threads.values():
            thread.join(timeout=5)
        self.threads.clear()
        
        self.db.end_session(self.session_id)
        self.is_monitoring = False
        self.toaster.show_toast("MidnightShift", "Monitoring Stopped", threaded=True)
        print(f"Monitoring stopped for session: {self.session_id}")
        self.session_id = None
        return True, "Monitoring stopped successfully."

app = Flask(__name__)
CORS(app)

db_manager = DatabaseManager()
monitor_manager = MonitoringManager(db_manager)
eye_tracking_stats = {}

@app.route('/api/start', methods=['POST'])
def start_route():
    success, message = monitor_manager.start()
    return jsonify({'success': success, 'message': message, 'session_id': monitor_manager.session_id})

@app.route('/api/stop', methods=['POST'])
def stop_route():
    success, message = monitor_manager.stop()
    return jsonify({'success': success, 'message': message})

@app.route('/api/status')
def status_route():
    return jsonify({'monitoring_active': monitor_manager.is_monitoring})

@app.route('/api/stats')
def stats_route():
    return jsonify({
        'today': db_manager.get_today_stats(),
        'recent_sessions': db_manager.get_all_sessions(),
        'top_distractions': db_manager.get_distraction_apps()
    })

@app.route('/api/eye-tracking/update', methods=['POST'])
def update_eye_tracking_route():
    global eye_tracking_stats
    eye_tracking_stats.update(request.json)
    return jsonify({'success': True})

@app.route('/api/eye-tracking')
def get_eye_tracking_route():
    return jsonify(eye_tracking_stats)

@app.route('/api/logs')
def get_logs_route():
    try:
        if os.path.exists("screen_activity.log"):
            with open("screen_activity.log", 'r', encoding='utf-8') as f:
                logs = f.readlines()
            return jsonify({'logs': [log.strip() for log in logs[-50:]]})
        else:
            return jsonify({'logs': ["Log file not created yet."]})
    except Exception as e:
        return jsonify({'logs': [f"Error reading logs: {e}"]})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)