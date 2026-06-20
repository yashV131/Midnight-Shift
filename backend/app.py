# app.py
import threading
import subprocess
import os
from datetime import datetime
from flask import Flask, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from win10toast import ToastNotifier

from database import DatabaseManager
from read_screen import ScreenMonitor
from eyetracking import EyeTracker

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

        try:
            eye_tracker = EyeTracker(self.stop_event)
            self.threads['eye'] = threading.Thread(target=eye_tracker.start_tracking, daemon=True)
        except Exception as e:
            print(f"EyeTracker failed to initialize: {e}")
            # don't fail the whole start sequence if eyetracking isn't available
        
        self.processes['lock'] = subprocess.Popen(['python', 'lockMechanism.py'])

        for thread in self.threads.values():
            thread.start()
        
        self.toaster.show_toast("ATLAS", "Monitoring Started", threaded=True)
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

        # Threads are daemon threads; signal them to stop and clear references.
        # Avoid joining here to prevent race conditions with threads that
        # may not have fully started.
        self.threads.clear()
        
        self.db.end_session(self.session_id)
        self.is_monitoring = False
        self.toaster.show_toast("ATLAS", "Monitoring Stopped", threaded=True)
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


@app.route('/api/auth/signup', methods=['POST'])
def signup_route():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required.'}), 400

    existing = db_manager.get_user_by_username(username)
    if existing:
        return jsonify({'success': False, 'message': 'User already exists.'}), 409

    password_hash = generate_password_hash(password)
    ok, err = db_manager.create_user(username, password_hash)
    if not ok:
        return jsonify({'success': False, 'message': f'Error creating user: {err}'}), 500

    return jsonify({'success': True, 'message': 'User created successfully.'})


@app.route('/api/auth/login', methods=['POST'])
def login_route():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required.'}), 400

    user = db_manager.get_user_by_username(username)
    if not user:
        return jsonify({'success': False, 'message': 'Invalid credentials.'}), 401

    if not check_password_hash(user['password_hash'], password):
        return jsonify({'success': False, 'message': 'Invalid credentials.'}), 401

    # Simple response - no tokens for now
    return jsonify({'success': True, 'message': 'Logged in successfully.', 'user': {'id': user['id'], 'username': user['username']}})

if __name__ == '__main__':
    # Disable the auto-reloader so background threads/processes started
    # by MonitoringManager are not lost when Flask watches file changes.
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)