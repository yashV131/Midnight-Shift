# database.py
import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_file="distraction_tracking.db"):
        self.db_file = db_file
        if not os.path.exists(self.db_file):
            self.init_database()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_file, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, start_time TIMESTAMP, end_time TIMESTAMP,
                    total_duration INTEGER, distraction_time INTEGER
                )''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS distraction_apps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, app_name TEXT UNIQUE,
                    visit_count INTEGER, total_time INTEGER
                )''')
            conn.commit()
            print("Database initialized or already exists.")

    def start_session(self):
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        with self._get_connection() as conn:
            conn.execute(
                'INSERT INTO sessions (id, start_time) VALUES (?, ?)',
                (session_id, datetime.now())
            )
            conn.commit()
        return session_id

    def end_session(self, session_id):
        if not session_id: return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT start_time, distraction_time FROM sessions WHERE id = ?', (session_id,))
            row = cursor.fetchone()
            if row:
                start_time = datetime.fromisoformat(row['start_time'])
                total_duration = int((datetime.now() - start_time).total_seconds())
                conn.execute(
                    'UPDATE sessions SET end_time = ?, total_duration = ? WHERE id = ?',
                    (datetime.now(), total_duration, session_id)
                )
                conn.commit()

    def log_app_visit(self, session_id, app_name, duration, is_distraction):
        with self._get_connection() as conn:
            if is_distraction:
                conn.execute(
                    'UPDATE sessions SET distraction_time = COALESCE(distraction_time, 0) + ? WHERE id = ?',
                    (duration, session_id)
                )
            
            cursor = conn.cursor()
            cursor.execute('SELECT visit_count, total_time FROM distraction_apps WHERE app_name = ?', (app_name,))
            row = cursor.fetchone()
            if row:
                new_visits = row['visit_count'] + 1
                new_time = row['total_time'] + duration if is_distraction else row['total_time']
                conn.execute(
                    'UPDATE distraction_apps SET visit_count = ?, total_time = ? WHERE app_name = ?',
                    (new_visits, new_time, app_name)
                )
            else:
                conn.execute(
                    'INSERT INTO distraction_apps (app_name, visit_count, total_time) VALUES (?, 1, ?)',
                    (app_name, duration if is_distraction else 0)
                )
            conn.commit()

    def get_today_stats(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT SUM(total_duration) as total, SUM(distraction_time) as distracted FROM sessions WHERE DATE(start_time) = ?",
                (today_str,)
            )
            stats = cursor.fetchone()
            total_time = stats['total'] or 0
            distraction_time = stats['distracted'] or 0
            distraction_percentage = (distraction_time / total_time * 100) if total_time > 0 else 0
            return {
                'total_time': total_time,
                'distraction_time': distraction_time,
                'distraction_percentage': round(distraction_percentage)
            }

    def get_all_sessions(self, limit=5):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sessions WHERE end_time IS NOT NULL ORDER BY start_time DESC LIMIT ?', (limit,))
            sessions = []
            for row in cursor.fetchall():
                total = row['total_duration'] or 0
                distracted = row['distraction_time'] or 0
                sessions.append({
                    'start_time': datetime.fromisoformat(row['start_time']).strftime('%b %d, %I:%M %p'),
                    'total_duration': total,
                    'distraction_time': distracted,
                    'distraction_percentage': round((distracted / total * 100) if total > 0 else 0)
                })
            return sessions

    def get_distraction_apps(self, limit=5):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM distraction_apps WHERE total_time > 0 ORDER BY total_time DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]