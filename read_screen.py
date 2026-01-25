import ctypes
import time
import os
import psutil
from datetime import datetime
from database import (
    start_session, end_session, log_app_visit, 
    get_session_stats, update_daily_stats
)
from win10toast import ToastNotifier

# Windows API constants
GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
GetWindowTextW = ctypes.windll.user32.GetWindowTextW
GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId

# Log file path
LOG_FILE = "screen_activity.log"

# Distraction keywords - apps/sites considered distracting
DISTRACTION_KEYWORDS = [
    "instagram", "facebook", "tiktok", "twitter", "reddit",
    "youtube", "twitch", "snapchat", "whatsapp", "messenger",
    "discord", "gaming", "game", "pornhub", "pinterest",
    "tumblr", "4chan"
]

# Initialize toaster for notifications
toaster = ToastNotifier()

def log_activity(message):
    """Log activity to both console and file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    clean_message = message.replace("⚠️", "[WARNING]").replace("✓", "[OK]").replace("🚨", "[ALERT]")
    log_message = f"[{timestamp}] {clean_message}"
    print(log_message)
    
    # Also write to log file
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    except Exception as e:
        print(f"Error writing to log file: {e}")

def extract_app_name(window_title):
    """Extract the main app/site name from window title"""
    separators = [' - ', ' | ', ' :: ', '(', '[']
    
    title_lower = window_title.lower().strip()
    
    earliest_sep_pos = len(title_lower)
    for sep in separators:
        pos = title_lower.find(sep.lower())
        if pos != -1 and pos < earliest_sep_pos:
            earliest_sep_pos = pos
    
    if earliest_sep_pos != len(title_lower):
        app_name = window_title[:earliest_sep_pos].strip()
    else:
        app_name = window_title.strip()
    
    suffixes_to_remove = ['chrome', 'firefox', 'safari', 'edge', 'explorer', 'whatsapp web']
    for suffix in suffixes_to_remove:
        if app_name.lower().endswith(suffix):
            app_name = app_name[:-len(suffix)].strip()
            break
    
    return app_name if app_name else window_title

def is_distracting(window_title, process_name):
    """Check if the current window/app is distracting"""
    combined = (window_title + " " + process_name).lower()
    return any(keyword in combined for keyword in DISTRACTION_KEYWORDS)

def send_distraction_notification(app_name, window_title):
    """Send a notification when distraction is detected"""
    try:
        toaster.show_toast(
            "🚨 Distraction Detected!",
            f"You're on {app_name}\n{window_title[:50]}...",
            duration=5,
            threaded=True
        )
    except Exception as e:
        print(f"Error sending notification: {e}")

def format_time(seconds):
    """Format seconds into HH:MM:SS format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_active_window_title():
    """Get the title of the currently active window"""
    try:
        hwnd = GetForegroundWindow()
        length = GetWindowTextLengthW(hwnd)
        
        if length == 0:
            return "Unknown Window"
        
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        return buf.value
    except Exception as e:
        return f"Error: {e}"

def get_active_window_process():
    """Get the process name of the currently active window"""
    try:
        hwnd = GetForegroundWindow()
        if hwnd is None or hwnd == 0:
            return "Unknown Process"
        
        pid = ctypes.c_ulong()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        if pid.value == 0:
            return "Unknown Process"
        
        process = psutil.Process(pid.value)
        return process.name()
    except Exception as e:
        return "Unknown Process"

def get_active_window_info():
    """Get full information about the active window"""
    title = get_active_window_title()
    process = get_active_window_process()
    return {
        'title': title,
        'process': process,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }

def monitor_window_changes(session_id, callback=None, check_interval=0.5, notification_interval=30):
    """Monitor active window changes"""
    last_window_title = ""
    last_process = ""
    last_notification_time = {}
    total_time = 0
    total_distraction_time = 0
    window_start_time = datetime.now()
    
    log_activity(f"✓ Started monitoring session: {session_id}")
    
    try:
        while True:
            try:
                current_title = get_active_window_title()
                current_process = get_active_window_process()
                
                if current_title != last_window_title:
                    # Calculate time spent on previous window
                    if last_window_title:
                        time_spent = (datetime.now() - window_start_time).total_seconds()
                        total_time += time_spent
                        
                        prev_app_name = extract_app_name(last_window_title)
                        is_prev_distraction = is_distracting(last_window_title, last_process)
                        
                        if is_prev_distraction:
                            total_distraction_time += time_spent
                        
                        # Log the previous window activity to database
                        log_app_visit(
                            session_id=session_id,
                            app_name=prev_app_name,
                            window_title=last_window_title,
                            process_name=last_process,
                            duration=int(time_spent),
                            is_distraction=is_prev_distraction
                        )
                    
                    app_name = extract_app_name(current_title)
                    
                    log_activity(f"[WINDOW/TAB CHANGED]")
                    log_activity(f"Application: {current_process}")
                    log_activity(f"Title: {current_title}")
                    log_activity(f"Time: {datetime.now().strftime('%H:%M:%S')}")
                    
                    # Check if it's distracting and send notification
                    if is_distracting(current_title, current_process):
                        current_time = datetime.now()
                        last_notif = last_notification_time.get(app_name, datetime.min)
                        
                        # Only send notification every notification_interval seconds per app
                        if (current_time - last_notif).total_seconds() > notification_interval:
                            send_distraction_notification(app_name, current_title)
                            last_notification_time[app_name] = current_time
                            log_activity(f"🚨 DISTRACTION ALERT: {app_name}")
                    
                    last_window_title = current_title
                    last_process = current_process
                    window_start_time = datetime.now()
                
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(check_interval)
    
    except KeyboardInterrupt:
        log_activity("⚠️ Monitoring interrupted by user")
    finally:
        # Always log final window and update stats when exiting
        if last_window_title:
            time_spent = (datetime.now() - window_start_time).total_seconds()
            total_time += time_spent
            prev_app_name = extract_app_name(last_window_title)
            is_prev_distraction = is_distracting(last_window_title, last_process)
            if is_prev_distraction:
                total_distraction_time += time_spent
            
            log_app_visit(
                session_id=session_id,
                app_name=prev_app_name,
                window_title=last_window_title,
                process_name=last_process,
                duration=int(time_spent),
                is_distraction=is_prev_distraction
            )
        
        # Update session and daily stats
        end_session(session_id, int(total_distraction_time))
        update_daily_stats(int(total_time), int(total_distraction_time))
        log_activity(f"✓ Session ended. Total: {int(total_time)}s, Distracted: {int(total_distraction_time)}s")

def start_continuous_monitoring(session_id=None):
    """Start continuous monitoring"""
    if session_id is None:
        session_id = start_session()
    
    try:
        monitor_window_changes(session_id, check_interval=0.5, notification_interval=30)
    except Exception as e:
        print(f"Error in continuous monitoring: {e}")
        log_activity(f"🚨 ERROR: {e}")
