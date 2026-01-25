from flask import Flask, render_template, jsonify, request
import subprocess
import os
import signal
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from win10toast import ToastNotifier

try:
    from database import (
        get_all_sessions, get_today_stats, get_distraction_apps,
        get_session_stats, init_database
    )
except ImportError as e:
    print(f"Database import error: {e}")

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Global variables
monitoring_processes = {
    'lock_mechanism': None,
    'read_screen': None,
    'eye_tracking': None,
    'session_id': None,
    'monitoring': False
}

eye_tracking_stats = {
    'blinks': 0,
    'productive_time': 0,
    'eyes_open': 0,
    'looking_at_screen': 0,
    'total_time': 0
}

toaster = ToastNotifier()

# Initialize database
try:
    init_database()
except Exception as e:
    print(f"Database initialization error: {e}")

def start_lock_mechanism():
    """Start the lock mechanism in a subprocess"""
    try:
        process = subprocess.Popen(
            ['python', 'lockMechanism.py'],
            cwd=os.path.dirname(__file__),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        monitoring_processes['lock_mechanism'] = process
        return True
    except Exception as e:
        print(f"Error starting lock mechanism: {e}")
        return False

def start_read_screen():
    """Start the read_screen monitoring in a thread"""
    try:
        from read_screen import start_continuous_monitoring
        
        # Run in a thread to keep notifications working
        monitoring_thread = threading.Thread(
            target=start_continuous_monitoring,
            kwargs={'session_id': monitoring_processes['session_id']},
            daemon=False
        )
        monitoring_thread.start()
        monitoring_processes['read_screen'] = monitoring_thread
        return True
    except Exception as e:
        print(f"Error starting read_screen: {e}")
        return False

def start_eye_tracking():
    """Start eye tracking in a subprocess"""
    try:
        from eyetracking import EyeTracker
        
        eye_tracker = EyeTracker()
        monitoring_thread = threading.Thread(
            target=eye_tracker.start_tracking,
            daemon=False
        )
        monitoring_thread.start()
        monitoring_processes['eye_tracking'] = monitoring_thread
        return True
    except Exception as e:
        print(f"Error starting eye tracking: {e}")
        return False

def stop_monitoring():
    """Stop all monitoring processes"""
    try:
        monitoring_processes['monitoring'] = False
        
        # Stop lock mechanism
        if monitoring_processes['lock_mechanism'] is not None:
            try:
                monitoring_processes['lock_mechanism'].terminate()
                monitoring_processes['lock_mechanism'].wait(timeout=5)
            except Exception as e:
                print(f"Error stopping lock mechanism: {e}")
            monitoring_processes['lock_mechanism'] = None
        
        # Stop read_screen thread
        if monitoring_processes['read_screen'] is not None:
            monitoring_processes['read_screen'] = None
        
        # Stop eye tracking
        if monitoring_processes['eye_tracking'] is not None:
            monitoring_processes['eye_tracking'] = None
        
        print("Monitoring stopped")
        return True
    except Exception as e:
        print(f"Error stopping monitoring: {e}")
        return False

@app.route('/api/start', methods=['POST'])
def start_all_monitoring():
    """Start monitoring"""
    try:
        if monitoring_processes['monitoring']:
            return jsonify({
                'success': False,
                'message': 'Monitoring already running'
            }), 400
        
        monitoring_processes['monitoring'] = True
        monitoring_processes['session_id'] = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Reset eye tracking stats
        eye_tracking_stats['blinks'] = 0
        eye_tracking_stats['productive_time'] = 0
        eye_tracking_stats['eyes_open'] = 0
        eye_tracking_stats['looking_at_screen'] = 0
        eye_tracking_stats['total_time'] = 0
        
        # Start all monitoring processes
        lock_started = start_lock_mechanism()
        read_screen_started = start_read_screen()
        eye_tracking_started = start_eye_tracking()
        
        if lock_started and read_screen_started and eye_tracking_started:
            toaster.show_toast(
                "Productivity Monitor",
                "Monitoring started successfully!",
                duration=3,
                threaded=True
            )
            return jsonify({
                'success': True,
                'message': 'Monitoring started successfully',
                'session_id': monitoring_processes['session_id']
            }), 200
        else:
            monitoring_processes['monitoring'] = False
            return jsonify({
                'success': False,
                'message': 'Failed to start all monitoring processes'
            }), 500
    except Exception as e:
        print(f"Error in start_monitoring: {e}")
        monitoring_processes['monitoring'] = False
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/stop', methods=['POST'])
def stop_all_monitoring():
    """Stop monitoring"""
    try:
        stop_monitoring()
        toaster.show_toast(
            "Productivity Monitor",
            "Monitoring stopped!",
            duration=3,
            threaded=True
        )
        return jsonify({
            'success': True,
            'message': 'Monitoring stopped successfully'
        }), 200
    except Exception as e:
        print(f"Error in stop_all_monitoring: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current monitoring status"""
    try:
        return jsonify({
            'monitoring_active': monitoring_processes['monitoring'],
            'session_id': monitoring_processes['session_id']
        }), 200
    except Exception as e:
        print(f"Status error: {e}")
        return jsonify({
            'monitoring_active': False,
            'error': str(e)
        }), 500

@app.route('/api/stats')
def get_statistics():
    """Get statistics and analytics"""
    try:
        today_stats = get_today_stats()
        all_sessions = get_all_sessions()
        distraction_apps = get_distraction_apps()
        
        stats_data = {
            'today': dict(today_stats) if today_stats else {
                'total_time': 0,
                'distraction_time': 0,
                'distraction_percentage': 0
            },
            'recent_sessions': [dict(session) for session in all_sessions[:10]] if all_sessions else [],
            'top_distractions': [dict(app) for app in distraction_apps[:10]] if distraction_apps else []
        }
        return jsonify(stats_data), 200
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({
            'error': str(e),
            'today': {},
            'recent_sessions': [],
            'top_distractions': []
        }), 500

@app.route('/api/eye-tracking')
def get_eye_tracking_stats():
    """Get eye tracking statistics"""
    try:
        return jsonify({
            'blinks': eye_tracking_stats['blinks'],
            'productive_time': eye_tracking_stats['productive_time'],
            'eyes_open': eye_tracking_stats['eyes_open'],
            'looking_at_screen': eye_tracking_stats['looking_at_screen'],
            'total_time': eye_tracking_stats['total_time']
        }), 200
    except Exception as e:
        print(f"Eye tracking stats error: {e}")
        return jsonify({
            'error': str(e),
            'blinks': 0,
            'productive_time': 0,
            'eyes_open': 0,
            'looking_at_screen': 0,
            'total_time': 0
        }), 500

@app.route('/api/eye-tracking/update', methods=['POST'])
def update_eye_tracking_stats():
    """Update eye tracking statistics"""
    try:
        data = request.json
        eye_tracking_stats['blinks'] = data.get('blinks', eye_tracking_stats['blinks'])
        eye_tracking_stats['productive_time'] = data.get('productive_time', eye_tracking_stats['productive_time'])
        eye_tracking_stats['eyes_open'] = data.get('eyes_open', eye_tracking_stats['eyes_open'])
        eye_tracking_stats['looking_at_screen'] = data.get('looking_at_screen', eye_tracking_stats['looking_at_screen'])
        eye_tracking_stats['total_time'] = data.get('total_time', eye_tracking_stats['total_time'])
        
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Eye tracking update error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """Get activity logs"""
    try:
        logs = []
        log_file = 'screen_activity.log'
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = f.readlines()[-100:]
                    logs = [log.strip() for log in logs]
            except Exception as e:
                print(f"Error reading log file: {e}")
                logs = [f"Error reading logs: {e}"]
        else:
            logs = ["No logs available yet. Start monitoring to generate logs."]
        
        return jsonify({
            'logs': logs,
            'total_logs': len(logs)
        }), 200
    except Exception as e:
        print(f"Logs error: {e}")
        return jsonify({
            'error': str(e),
            'logs': []
        }), 500

@app.route('/api/productive-apps')
def get_productive_apps():
    """Get productive apps from activity logs"""
    try:
        productive_apps = {}
        log_file = 'screen_activity.log'
        
        # List of productive keywords
        productive_keywords = [
            'vs code', 'visual studio', 'pycharm', 'sublime', 'atom',
            'github', 'gitlab', 'stackoverflow', 'documentation',
            'google docs', 'notion', 'confluence', 'jira',
            'slack', 'email', 'calendar', 'excel', 'sheets',
            'figma', 'adobe', 'blender', 'chrome', 'firefox'
        ]
        
        # Distraction keywords to exclude
        distraction_keywords = [
            'instagram', 'facebook', 'tiktok', 'twitter', 'reddit',
            'youtube', 'twitch', 'snapchat', 'whatsapp', 'messenger',
            'discord', 'gaming', 'game', 'pornhub', 'pinterest',
            'tumblr', '4chan'
        ]
        
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                current_app = None
                current_title = None
                start_time = None
                
                for line in lines:
                    # Check for title line
                    if '[WINDOW/TAB CHANGED]' in line or 'Title:' in line:
                        if 'Title:' in line:
                            current_title = line.split('Title:')[1].strip()
                            
                            # Check if it's productive
                            is_productive = False
                            is_distraction = False
                            
                            combined = current_title.lower()
                            
                            # Check if distraction
                            for keyword in distraction_keywords:
                                if keyword in combined:
                                    is_distraction = True
                                    break
                            
                            # If not distraction, check if productive
                            if not is_distraction:
                                for keyword in productive_keywords:
                                    if keyword in combined:
                                        is_productive = True
                                        break
                            
                            # If neither, mark as productive (neutral apps)
                            if not is_distraction and not is_productive and current_title != 'Unknown Window':
                                is_productive = True
                            
                            if is_productive and not is_distraction:
                                if current_title not in productive_apps:
                                    productive_apps[current_title] = 0
                    
                    # Track time
                    if '[WINDOW/TAB CHANGED]' in line:
                        # Extract timestamp
                        if '[' in line and ']' in line:
                            try:
                                time_str = line[line.find('[')+1:line.find(']')]
                                start_time = time_str
                            except:
                                pass
                
                # Calculate durations from logs (approximate 0.5s per log entry)
                for app in productive_apps:
                    # Count occurrences and multiply by check interval
                    productive_apps[app] = productive_apps[app] * 0.5
                
                # Sort by time spent
                sorted_apps = sorted(productive_apps.items(), key=lambda x: x[1], reverse=True)
                
                return jsonify({
                    'productive_apps': [
                        {'app_name': app, 'time_spent': int(time)} 
                        for app, time in sorted_apps
                    ]
                }), 200
            except Exception as e:
                print(f"Error parsing logs: {e}")
                return jsonify({'productive_apps': [], 'error': str(e)}), 500
        else:
            return jsonify({'productive_apps': []}), 200
    except Exception as e:
        print(f"Productive apps error: {e}")
        return jsonify({'productive_apps': [], 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    print(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='127.0.0.1')