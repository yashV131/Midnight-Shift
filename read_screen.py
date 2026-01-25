import ctypes
import psutil
import time
from datetime import datetime
from win10toast import ToastNotifier

class ScreenMonitor:
    def __init__(self, session_id, stop_event, db_manager):
        self.session_id = session_id
        self.stop_event = stop_event
        self.db = db_manager
        self.log_file = "screen_activity.log"
        self.toaster = ToastNotifier()
        self.canonical_apps = {
            " instagram ": "Instagram",
            " facebook ": "Facebook",
            " youtube ": "YouTube",
            " whatsapp ": "Whatsapp",
            " twitter ": "Twitter",
            " tiktok ": "TikTok",
            " reddit ": "Reddit",
            " snapchat ": "Snapchat",
            " pinterest ": "Pinterest",
           " messenger ": "Messenger",
            " discord ": "Discord",
            " twitch ": "Twitch",
            " netflix ": "Netflix",
            " hulu ": "Hulu",
            " hbo ": "HBO",
            " disney ": "Disney"
        }

    def _get_active_window_info(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_ulong()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process_name = psutil.Process(pid.value).name()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return {'process': process_name, 'title': buf.value}
        except Exception:
            return {'process': 'Unknown', 'title': 'Unknown'}

    def _get_canonical_app(self, title, process):
        combined = (title + " " + process).lower()
        for keyword, name in self.canonical_apps.items():
            if keyword in combined:
                return name
        return None

    def _is_distracting(self, title, process):
        return self._get_canonical_app(title, process) is not None

    def _log(self, message):
        log_entry = message + "\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def start_monitoring(self, interval=2.0):
        self._log("Session started!")
        last_info = self._get_active_window_info()
        last_canonical = self._get_canonical_app(last_info['title'], last_info['process']) or last_info['title']
        start_time = datetime.now()
        while not self.stop_event.is_set():
            time.sleep(interval)
            current_info = self._get_active_window_info()
            current_canonical = self._get_canonical_app(current_info['title'], current_info['process']) or current_info['title']
            if current_canonical != last_canonical:
                duration = int((datetime.now() - start_time).total_seconds())
                is_distraction = self._is_distracting(last_info['title'], last_info['process'])
                self.db.log_app_visit(self.session_id, last_canonical, duration, is_distraction)
                distraction_msg = " (Distraction detected!)" if is_distraction else ""
                self._log(f"Switched from '{last_canonical}' after {duration} seconds{distraction_msg}.")
                last_canonical = current_canonical
                last_info = current_info
                start_time = datetime.now()
                if self._is_distracting(current_info['title'], current_info['process']):
                    self.toaster.show_toast("Distraction Alert!", f"Switched to {current_canonical}", threaded=True)
        duration = int((datetime.now() - start_time).total_seconds())
        is_distraction = self._is_distracting(last_info['title'], last_info['process'])
        self.db.log_app_visit(self.session_id, last_canonical, duration, is_distraction)
        distraction_msg = " (Distraction detected!)" if is_distraction else ""
        self._log(f"Session ended. Last app was '{last_canonical}' for {duration} seconds{distraction_msg}.")
        print("ScreenMonitor stopped.")