import cv2
import dlib
import time
import ctypes
import requests
from datetime import datetime

# ---------------- CONFIG ----------------
EYE_CLOSED_FRAMES_ALERT = 15   # frames eyes closed to trigger fatigue
DISTRACTION_SECONDS = 10       # seconds looking away to trigger distraction alert
FRAME_RATE = 30                # approximate webcam FPS
LOOK_AWAY_THRESHOLD = 0.25     # fraction of frame away from center to detect looking away
PREDICTOR_PATH = r"C:/Users/ayala/OneDrive/Documents/tamuhack/shape_predictor_68_face_landmarks.dat"
# ---------------------------------------

# Load dlib face detector and landmark predictor
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(PREDICTOR_PATH)

# Counters
closed_frames = 0
total_blinks = 0
productive_time = 0
prev_eyes_open = True
last_facing_time = time.time()
timer_paused = False

# ---------------- SESSION SETUP ----------------
mode = input("Choose session type: (1) Timer, (2) Stopwatch: ")
if mode == "1":
    session_minutes = float(input("Enter session time in minutes: "))
    session_seconds = session_minutes * 60
else:
    session_seconds = None  # stopwatch mode

# Initialize webcam
cap = cv2.VideoCapture(0)
start_time = time.time()

def send_notification(title, message):
    """Send a Windows notification"""
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x1)

def eye_aspect_ratio(eye_points):
    """Simple EAR: ratio of vertical distance to horizontal distance"""
    top = eye_points[1].y - eye_points[5].y
    bottom = eye_points[2].y - eye_points[4].y
    horizontal = eye_points[0].x - eye_points[3].x
    return (abs(top) + abs(bottom)) / (2 * abs(horizontal) + 1e-6)

def is_eye_open(eye_points, threshold=0.2):
    return eye_aspect_ratio(eye_points) > threshold

def face_center(face):
    return (face.left() + face.width() // 2, face.top() + face.height() // 2)

def start_tracking():
    """Start eye tracking and send stats to Flask backend"""
    blinks = 0
    eyes_open_time = 0
    looking_at_screen_time = 0
    productive_time = 0
    start_time = datetime.now()
    
    while True:
        try:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = detector(gray)

            eyes_open = False
            looking_at_screen = False

            for face in faces:
                landmarks = predictor(gray, face)

                left_eye = [landmarks.part(i) for i in range(36, 42)]
                right_eye = [landmarks.part(i) for i in range(42, 48)]

                if is_eye_open(left_eye) or is_eye_open(right_eye):
                    eyes_open = True

                # Draw landmarks
                for point in left_eye + right_eye:
                    cv2.circle(frame, (point.x, point.y), 2, (0, 255, 0), -1)

                # Face position relative to center
                fx, fy = face_center(face)
                h, w = frame.shape[:2]
                if (w * LOOK_AWAY_THRESHOLD < fx < w * (1 - LOOK_AWAY_THRESHOLD) and
                    h * LOOK_AWAY_THRESHOLD < fy < h * (1 - LOOK_AWAY_THRESHOLD)):
                    looking_at_screen = True
                    last_facing_time = time.time()

            # Blink detection
            if eyes_open:
                if not prev_eyes_open:
                    total_blinks += 1
                closed_frames = 0
                if not timer_paused:
                    productive_time += 1 / FRAME_RATE
            else:
                closed_frames += 1
                if closed_frames >= EYE_CLOSED_FRAMES_ALERT:
                    cv2.putText(frame, "You may be getting distracted!", (50, 200),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 3)
                    closed_frames = 0

            prev_eyes_open = eyes_open

            # Pause timer if looking away
            timer_paused = not looking_at_screen

            # Distraction notification
            if timer_paused and time.time() - last_facing_time > DISTRACTION_SECONDS:
                send_notification("Attention Alert", "You may be getting distracted!")
                last_facing_time = time.time()  # reset after notification

            # Display info
            elapsed = time.time() - start_time
            remaining = session_seconds - elapsed if session_seconds else elapsed

            cv2.putText(frame, f"Blinks: {total_blinks}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0),2)
            cv2.putText(frame, f"Productive Time (s): {int(productive_time)}", (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0),2)
            cv2.putText(frame, f"Eyes Open: {eyes_open}", (10,90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255),2)
            cv2.putText(frame, f"Looking at Screen: {looking_at_screen}", (10,120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255),2)
            if session_seconds:
                cv2.putText(frame, f"Time Remaining: {int(remaining)}s", (10,150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255),2)

            cv2.imshow("Eye Tracking Productivity", frame)

            # Send stats to Flask every 5 seconds
            if int(elapsed) % 5 == 0:
                total_time = elapsed
                eyes_open_percent = (productive_time / total_time * 100) if total_time > 0 else 0
                looking_at_screen_percent = (looking_at_screen_time / total_time * 100) if total_time > 0 else 0
                
                try:
                    requests.post(f'http://127.0.0.1:5000/api/eye-tracking/update', json={
                        'blinks': total_blinks,
                        'eyes_open': eyes_open_percent,
                        'looking_at_screen': looking_at_screen_percent,
                        'productive_time': int(productive_time),
                        'total_time': int(total_time)
                    })
                except:
                    pass

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            # End session if timer mode
            if session_seconds and elapsed >= session_seconds:
                break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(0.1)

    cap.release()
    cv2.destroyAllWindows()

    print("\n--- SESSION SUMMARY ---")
    print(f"Total productive time (s): {int(productive_time)}")
    print(f"Total blinks: {total_blinks}")
    if productive_time / max(1, elapsed) > 0.7:
        print("You were highly productive!")
    elif productive_time / max(1, elapsed) > 0.4:
        print("Moderate productivity.")
    else:
        print("Low productivity, consider improving focus.")
