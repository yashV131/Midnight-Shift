import cv2
import dlib
import time
import ctypes
import face_recognition
import os
import sys
import winsound
import numpy as np
from collections import deque

# =========================
# CONFIG
# =========================
DISTRACTION_SECONDS = 10
BREAK_MINUTES = 20
BREAK_SECONDS = BREAK_MINUTES * 60

LOOK_AWAY_THRESHOLD = 0.25
EYE_CLOSED_THRESHOLD = 2.0

LOCK_BUFFER = 5
OWNER_GRACE_SECONDS = 2.5
PERSON_GRACE_SECONDS = 3.0

POSTURE_THRESHOLD = 18
FACE_CHECK_INTERVAL = 5

PREDICTOR_PATH = "shape_predictor_68_face_landmarks.dat"

# =========================
# SYSTEM FUNCTIONS
# =========================
def send_notification(title, message):
    ctypes.windll.user32.MessageBoxW(
        0, message, title, 0x40 | 0x1
    )

def lock_laptop():
    if sys.platform == "win32":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    elif sys.platform == "darwin":
        os.system("pmset displaysleepnow")
    else:
        os.system("gnome-screensaver-command -l")

# =========================
# MODELS
# =========================
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(PREDICTOR_PATH)

hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

# =========================
# HELPERS
# =========================
def eye_aspect_ratio(eye):
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return (A + B) / (2.0 * C + 1e-6)

# =========================
# STATE VARIABLES
# =========================
productive_time = 0.0
productive_start = None

eye_closed_start = None
total_blinks = 0

last_facing_time = time.time()
last_focus_time = time.time()

last_owner_verified_time = time.time()
last_person_seen_time = time.time()

timer_paused = False
out_of_frame_start = None

ear_y_history = deque(maxlen=5)
frame_count = 0

# =========================
# SESSION SETUP
# =========================
mode = input("Choose session type: (1) Timer, (2) Stopwatch: ")
session_seconds = None
if mode == "1":
    session_seconds = float(input("Enter minutes: ")) * 60

cap = cv2.VideoCapture(0)
start_time = time.time()

# =========================
# OWNER REGISTRATION
# =========================
owner_encoding = None
baseline_ear_y = None

print("Press 's' to register owner.")
while True:
    ret, frame = cap.read()
    if not ret:
        continue

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = detector(rgb)

    cv2.imshow("Registration", frame)
    if cv2.waitKey(1) & 0xFF == ord("s"):
        encs = face_recognition.face_encodings(rgb)
        if encs and faces:
            owner_encoding = encs[0]
            landmarks = predictor(rgb, faces[0])
            baseline_ear_y = landmarks.part(1).y
            print("Owner registered.")
            break

cv2.destroyWindow("Registration")

# =========================
# MAIN LOOP
# =========================
prev_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = frame.shape[:2]

    # -------------------------
    # PERSON DETECTION (DEBOUNCED)
    # -------------------------
    rects, _ = hog.detectMultiScale(frame)
    if len(rects) > 0:
        last_person_seen_time = time.time()

    person_detected = (
        time.time() - last_person_seen_time
        < PERSON_GRACE_SECONDS
    )

    # -------------------------
    # FACE / EYE TRACKING
    # -------------------------
    faces = detector(gray)
    looking_at_screen = False
    both_eyes_open = False

    for face in faces:
        landmarks = predictor(gray, face)

        left_eye = np.array([
            (landmarks.part(i).x, landmarks.part(i).y)
            for i in range(36, 42)
        ])
        right_eye = np.array([
            (landmarks.part(i).x, landmarks.part(i).y)
            for i in range(42, 48)
        ])

        left_ear = eye_aspect_ratio(left_eye)
        right_ear = eye_aspect_ratio(right_eye)

        both_eyes_open = (
            left_ear > 0.22 and right_ear > 0.22
        )

        nose = landmarks.part(30)
        fx = nose.x

        if w * LOOK_AWAY_THRESHOLD < fx < w * (1 - LOOK_AWAY_THRESHOLD):
            looking_at_screen = True
            last_facing_time = time.time()

        # posture tracking
        ear_y_history.append(landmarks.part(1).y)

        cv2.rectangle(
            frame,
            (face.left(), face.top()),
            (face.right(), face.bottom()),
            (0, 255, 0),
            2,
        )

    # -------------------------
    # OWNER VERIFICATION (STICKY)
    # -------------------------
    if frame_count % FACE_CHECK_INTERVAL == 0:
        encs = face_recognition.face_encodings(rgb)
        if encs:
            match = face_recognition.compare_faces(
                [owner_encoding], encs[0], tolerance=0.5
            )[0]
            if match:
                last_owner_verified_time = time.time()

    owner_verified = (
        time.time() - last_owner_verified_time
        < OWNER_GRACE_SECONDS
    )

    # -------------------------
    # SECURITY LOCK (STRICT)
    # -------------------------
    if not owner_verified and not person_detected:
        if out_of_frame_start is None:
            out_of_frame_start = time.time()
    else:
        out_of_frame_start = None

    if out_of_frame_start:
        if time.time() - out_of_frame_start >= LOCK_BUFFER:
            lock_laptop()
            break

    # -------------------------
    # POSTURE ALERT
    # -------------------------
    if baseline_ear_y and ear_y_history:
        avg_y = sum(ear_y_history) / len(ear_y_history)
        if avg_y > baseline_ear_y + POSTURE_THRESHOLD:
            cv2.putText(
                frame,
                "SIT UP!",
                (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                2,
                (0, 0, 255),
                4,
            )
            winsound.Beep(1200, 50)

    # -------------------------
    # BLINK LOGIC
    # -------------------------
    if both_eyes_open:
        if eye_closed_start:
            if time.time() - eye_closed_start <= EYE_CLOSED_THRESHOLD:
                total_blinks += 1
            eye_closed_start = None
    else:
        if eye_closed_start is None:
            eye_closed_start = time.time()

    # -------------------------
    # PRODUCTIVITY TIMER
    # -------------------------
    paused = (
        not looking_at_screen
        or (
            eye_closed_start
            and time.time() - eye_closed_start
            > EYE_CLOSED_THRESHOLD
        )
    )

    if timer_paused and not paused:
        productive_start = time.time()
    elif not timer_paused and paused:
        if productive_start:
            productive_time += time.time() - productive_start
            productive_start = None

    timer_paused = paused

    # -------------------------
    # ALERTS
    # -------------------------
    if paused and time.time() - last_facing_time > DISTRACTION_SECONDS:
        send_notification("Attention", "You may be distracted.")
        last_facing_time = time.time()

    if not paused and time.time() - last_focus_time > BREAK_SECONDS:
        send_notification("Eye Break", "Look away for 20 seconds.")
        last_focus_time = time.time()
    elif paused:
        last_focus_time = time.time()

    # -------------------------
    # DISPLAY
    # -------------------------
    display_time = productive_time
    if productive_start:
        display_time += time.time() - productive_start

    cv2.putText(frame, f"Blinks: {total_blinks}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    cv2.putText(frame, f"Productive: {int(display_time)}s", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"Owner OK: {owner_verified}", (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    fps = int(1 / (time.time() - prev_time))
    prev_time = time.time()
    cv2.putText(frame, f"FPS: {fps}", (10, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    cv2.imshow("Security & Productivity", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
    if session_seconds and time.time() - start_time >= session_seconds:
        break

# =========================
# CLEANUP
# =========================
if productive_start:
    productive_time += time.time() - productive_start

cap.release()
cv2.destroyAllWindows()

print("\n--- SESSION SUMMARY ---")
print(f"Productive time: {int(productive_time)}s")
print(f"Total blinks: {total_blinks}")
