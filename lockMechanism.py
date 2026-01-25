import cv2
import face_recognition
import os
import sys
import time
from ultralytics import YOLO
import winsound
from collections import deque

# =========================
# System Lock Function
# =========================
def lock_laptop():
    if sys.platform == "win32":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    elif sys.platform == "darwin":
        os.system("pmset displaysleepnow")
    else:
        os.system("gnome-screensaver-command -l")

# =========================
# Models & Camera
# =========================
pose_model = YOLO("yolo11n-pose.pt")

video_capture = cv2.VideoCapture(0)

# Reduce camera resolution (BIG speedup)
video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# =========================
# State Variables
# =========================
owner_encoding = None
baseline_y = None
out_of_frame_start = None
lock_buffer = 5
threshold = 25

ear_y_history = deque(maxlen=5)

frame_count = 0
FACE_CHECK_INTERVAL = 5  # run face recognition every 5 frames

print("--- TAMUHack: Strict Security & Posture ---")

# =========================
# OWNER REGISTRATION
# =========================
while True:
    ret, frame = video_capture.read()
    if not ret:
        continue

    cv2.imshow("Registration", frame)

    if cv2.waitKey(1) & 0xFF == ord("s"):
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

        face_encodings = face_recognition.face_encodings(small_frame)
        pose_results = pose_model(small_frame, verbose=False)

        if face_encodings and len(pose_results[0].keypoints.data) > 0:
            owner_encoding = face_encodings[0]
            baseline_y = pose_results[0].keypoints.data[0][3][1].item()
            print("Owner Registered.")
            break

cv2.destroyWindow("Registration")

# =========================
# MAIN LOOP
# =========================
prev_time = time.time()

while True:
    ret, frame = video_capture.read()
    if not ret:
        break

    frame_count += 1

    # Resize frame BEFORE processing
    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

    # -------------------------
    # Pose Detection (YOLO)
    # -------------------------
    pose_results = pose_model(small_frame, verbose=False)
    person_detected = len(pose_results[0].keypoints.data) > 0

    # -------------------------
    # Face Recognition (throttled)
    # -------------------------
    owner_verified = False
    face_encodings = []

    if frame_count % FACE_CHECK_INTERVAL == 0:
        face_locations = face_recognition.face_locations(small_frame)
        face_encodings = face_recognition.face_encodings(
            small_frame, face_locations
        )

        if face_encodings:
            matches = face_recognition.compare_faces(
                [owner_encoding], face_encodings[0], tolerance=0.5
            )
            owner_verified = True in matches

    # -------------------------
    # SECURITY LOGIC
    # -------------------------
    if not owner_verified:
        if face_encodings:
            print("Unauthorized face detected!")
            if out_of_frame_start is None:
                out_of_frame_start = time.time()

        elif not person_detected:
            if out_of_frame_start is None:
                out_of_frame_start = time.time()

        else:
            if out_of_frame_start is None:
                out_of_frame_start = time.time()
    else:
        out_of_frame_start = None

    # -------------------------
    # LOCK TIMER
    # -------------------------
    if out_of_frame_start is not None:
        elapsed = time.time() - out_of_frame_start
        remaining = max(0, int(lock_buffer - elapsed))

        status_msg = f"SECURITY ALERT: LOCKING IN {remaining}s"
        msg_color = (0, 0, 255)

        if elapsed >= lock_buffer:
            lock_laptop()
            break
    else:
        status_msg = "OWNER VERIFIED"
        msg_color = (0, 255, 0)

    # -------------------------
    # POSTURE LOGIC
    # -------------------------
    if person_detected and owner_verified:
        current_y = pose_results[0].keypoints.data[0][3][1].item()
        ear_y_history.append(current_y)

        avg_ear_y = sum(ear_y_history) / len(ear_y_history)

        if avg_ear_y > (baseline_y + threshold):
            cv2.putText(
                frame,
                "SIT UP!",
                (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                2,
                (0, 0, 255),
                5,
            )
            winsound.Beep(1200, 50)

    # -------------------------
    # FPS Counter
    # -------------------------
    fps = 1 / (time.time() - prev_time)
    prev_time = time.time()

    cv2.putText(frame, f"FPS: {int(fps)}", (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

    cv2.putText(frame, status_msg, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, msg_color, 2)

    cv2.imshow("Security & Posture", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

video_capture.release()
cv2.destroyAllWindows()
