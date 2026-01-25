import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_FILE = "distraction_tracking.db"

def init_database():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Create sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                total_duration INTEGER,
                productive_time INTEGER,
                distraction_time INTEGER,
                distraction_percentage REAL
            )
        ''')
        
        # Create daily_stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE,
                total_time INTEGER,
                distraction_time INTEGER,
                productive_time INTEGER,
                distraction_percentage REAL
            )
        ''')
        
        # Create distraction_apps table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS distraction_apps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_name TEXT,
                visit_count INTEGER,
                total_time INTEGER
            )
        ''')
        
        conn.commit()
        print("Database initialized successfully")
    except sqlite3.OperationalError as e:
        print(f"Database initialization error: {e}")
    finally:
        conn.close()

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Database error: {e}")
    finally:
        conn.close()

def start_session():
    """Start a new tracking session"""
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (id, start_time, total_duration, productive_time, distraction_time, distraction_percentage)
            VALUES (?, ?, 0, 0, 0, 0)
        ''', (session_id, datetime.now()))
    
    return session_id

def end_session(session_id, total_distraction_time):
    """End a tracking session"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get session start time
        cursor.execute('SELECT start_time FROM sessions WHERE id = ?', (session_id,))
        result = cursor.fetchone()
        
        if result:
            start_time = datetime.fromisoformat(result['start_time'])
            end_time = datetime.now()
            total_duration = int((end_time - start_time).total_seconds())
            productive_time = total_duration - total_distraction_time
            distraction_percentage = (total_distraction_time / total_duration * 100) if total_duration > 0 else 0
            
            cursor.execute('''
                UPDATE sessions
                SET end_time = ?, total_duration = ?, productive_time = ?, 
                    distraction_time = ?, distraction_percentage = ?
                WHERE id = ?
            ''', (end_time, total_duration, productive_time, total_distraction_time, distraction_percentage, session_id))

def log_app_visit(session_id, app_name, window_title, process_name, duration, is_distraction):
    """Log an individual app/site visit"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Update or insert distraction app
        cursor.execute('''
            SELECT id FROM distraction_apps WHERE app_name = ?
        ''', (app_name,))
        
        result = cursor.fetchone()
        
        if result:
            cursor.execute('''
                UPDATE distraction_apps
                SET visit_count = visit_count + 1, total_time = total_time + ?
                WHERE app_name = ?
            ''', (duration if is_distraction else 0, app_name))
        else:
            cursor.execute('''
                INSERT INTO distraction_apps (app_name, visit_count, total_time)
                VALUES (?, 1, ?)
            ''', (app_name, duration if is_distraction else 0))

def get_session_stats(session_id):
    """Get statistics for a specific session"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM sessions WHERE id = ?
        ''', (session_id,))
        return cursor.fetchone()

def get_today_stats():
    """Get today's statistics from sessions"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get stats from today's sessions
        cursor.execute('''
            SELECT 
                SUM(total_duration) as total_time,
                SUM(distraction_time) as distraction_time,
                SUM(productive_time) as productive_time
            FROM sessions
            WHERE DATE(start_time) = ?
        ''', (today,))
        
        result = cursor.fetchone()
        
        if result and result['total_time']:
            total_time = result['total_time'] or 0
            distraction_time = result['distraction_time'] or 0
            productive_time = result['productive_time'] or 0
            distraction_percentage = (distraction_time / total_time * 100) if total_time > 0 else 0
            
            return {
                'total_time': total_time,
                'distraction_time': distraction_time,
                'productive_time': productive_time,
                'distraction_percentage': distraction_percentage
            }
        else:
            return {
                'total_time': 0,
                'distraction_time': 0,
                'productive_time': 0,
                'distraction_percentage': 0
            }

def update_daily_stats(total_time, distraction_time):
    """Update or create daily statistics"""
    today = datetime.now().strftime('%Y-%m-%d')
    productive_time = total_time - distraction_time
    distraction_percentage = (distraction_time / total_time * 100) if total_time > 0 else 0
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM daily_stats WHERE date = ?', (today,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE daily_stats
                SET total_time = ?, distraction_time = ?, productive_time = ?, distraction_percentage = ?
                WHERE date = ?
            ''', (total_time, distraction_time, productive_time, distraction_percentage, today))
        else:
            cursor.execute('''
                INSERT INTO daily_stats (date, total_time, distraction_time, productive_time, distraction_percentage)
                VALUES (?, ?, ?, ?, ?)
            ''', (today, total_time, distraction_time, productive_time, distraction_percentage))

def get_all_sessions():
    """Get all tracking sessions"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, start_time, total_duration, distraction_time, distraction_percentage
            FROM sessions
            WHERE end_time IS NOT NULL
            ORDER BY start_time DESC
            LIMIT 50
        ''')
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row['id'],
                'start_time': row['start_time'],
                'total_duration': row['total_duration'] or 0,
                'distraction_time': row['distraction_time'] or 0,
                'distraction_percentage': row['distraction_percentage'] or 0
            })
        return sessions

def get_distraction_apps():
    """Get top distracting apps"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT app_name, visit_count, total_time
            FROM distraction_apps
            ORDER BY total_time DESC, visit_count DESC
            LIMIT 20
        ''')
        
        apps = []
        for row in cursor.fetchall():
            apps.append({
                'app_name': row['app_name'],
                'visit_count': row['visit_count'],
                'total_time': row['total_time']
            })
        return apps

# Initialize database on import
if not os.path.exists(DB_FILE):
    init_database()
else:
    try:
        init_database()
    except:
        pass
