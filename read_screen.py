import ctypes
import time
from datetime import datetime
import psutil
import threading
import os

# Windows API constants
GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
GetWindowTextW = ctypes.windll.user32.GetWindowTextW
GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId

# Log file path
LOG_FILE = "screen_activity.log"

def log_activity(message):
    """Log activity to both console and file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    
    # Also write to log file
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_message + "\n")
    except Exception as e:
        print(f"Error writing to log: {e}")

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
        pid = ctypes.c_ulong()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        process = psutil.Process(pid.value)
        return process.name()
    except Exception as e:
        return f"Unknown Process"

def get_active_window_info():
    """Get full information about the active window"""
    title = get_active_window_title()
    process = get_active_window_process()
    return {
        'title': title,
        'process': process,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }

def monitor_window_changes(callback=None, check_interval=0.5):
    """Monitor for window/tab changes continuously
    
    Args:
        callback: Function to call when window changes. Receives window info dict.
        check_interval: How often to check for changes in seconds (default 0.5s for frequent updates)
    """
    last_window = None
    last_title = None
    
    log_activity("="*60)
    log_activity("Screen Monitor Started - Continuously Reading Screen")
    log_activity("="*60)
    
    try:
        while True:
            current_info = get_active_window_info()
            current_window = f"{current_info['process']}:{current_info['title']}"
            current_title = current_info['title']
            
            # Check if window or tab changed
            if last_window is None or current_window != last_window:
                log_activity(f"✓ WINDOW/TAB CHANGED")
                log_activity(f"  Application: {current_info['process']}")
                log_activity(f"  Title: {current_info['title']}")
                log_activity(f"  Time: {current_info['timestamp']}")
                log_activity("")
                
                if callback:
                    callback(current_info)
                
                last_window = current_window
                last_title = current_title
            
            time.sleep(check_interval)
    
    except KeyboardInterrupt:
        log_activity("\n" + "="*60)
        log_activity("Screen Monitor stopped by user")
        log_activity("="*60)

def get_screen_info():
    """Get current screen information and display it"""
    info = get_active_window_info()
    print("\n" + "="*50)
    print("CURRENT SCREEN INFORMATION")
    print("="*50)
    print(f"Time: {info['timestamp']}")
    print(f"Application: {info['process']}")
    print(f"Window Title: {info['title']}")
    print("="*50 + "\n")
    return info

def start_continuous_monitoring():
    """Start continuous screen monitoring in background"""
    log_activity("Starting continuous screen monitoring...")
    monitor_window_changes(check_interval=0.5)  # Check every 0.5 seconds

if __name__ == "__main__":
    # Display current window info first
    get_screen_info()
    
    # Start continuous monitoring
    start_continuous_monitoring()
