import cv2
import face_recognition
import os
import sys
import time
from ultralytics import YOLO
import winsound
from collections import deque

def lock_laptop():
    if sys.platform == "win32":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    elif sys.platform == "darwin":
        os.system("pmset displaysleepnow")
    else:
        os.system("gnome-screensaver-command -l")

pose_model = YOLO('yolo11n-pose.pt')
video_capture = cv2.VideoCapture(0)

owner_encoding = None
baseline_y = None
out_of_frame_start = None  
lock_buffer = 5            
threshold = 25 
ear_y_history = deque(maxlen=5)

print("--- TAMUHack: Strict Security & Posture ---")
while True:
    ret, frame = video_capture.read()
    cv2.imshow('Registration', frame)
    if cv2.waitKey(1) & 0xFF == ord('s'):
        face_encodings = face_recognition.face_encodings(frame)
        pose_results = pose_model(frame, verbose=False)
        if face_encodings and len(pose_results[0].keypoints.data) > 0:
            owner_encoding = face_encodings[0]
            baseline_y = pose_results[0].keypoints.data[0][3][1].item()
            print("Owner Registered.")
            break

cv2.destroyWindow('Registration')

while True:
    ret, frame = video_capture.read()
    if not ret: break

    # 1. Run Detectors
    pose_results = pose_model(frame, verbose=False)
    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)
    
    person_detected = len(pose_results[0].keypoints.data) > 0
    owner_verified = False

    # 2. Check if the face in frame is the OWNER
    if face_encodings:
        matches = face_recognition.compare_faces([owner_encoding], face_encodings[0], tolerance=0.5) # Stricter tolerance
        if True in matches:
            owner_verified = True

    # 3. STRICT SECURITY LOGIC
    # If a face is present but NOT the owner, or if no one is there at all:
    if not owner_verified:
        # If there's a face that ISN'T you, start locking immediately (no grace period for strangers)
        if len(face_encodings) > 0:
            print("Unauthorized face detected!")
            if out_of_frame_start is None: out_of_frame_start = time.time()
        # If no one is detected at all, start the 5-second buffer
        elif not person_detected:
            if out_of_frame_start is None: out_of_frame_start = time.time()
        # If a body is seen (side profile) but no face, we allow the 5-second buffer to run
        else:
            if out_of_frame_start is None: out_of_frame_start = time.time()
    else:
        # Owner is verified, reset the timer
        out_of_frame_start = None

    # 4. Handle Timer and Locking
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

    # 5. POSTURE LOGIC
    if person_detected and owner_verified:
        current_y = pose_results[0].keypoints.data[0][3][1].item()
        ear_y_history.append(current_y)
        avg_ear_y = sum(ear_y_history) / len(ear_y_history)

        if avg_ear_y > (baseline_y + threshold):
            cv2.putText(frame, "SIT UP!", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 2, (0,0,255), 5)
            winsound.Beep(1200, 50)

    cv2.putText(frame, status_msg, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, msg_color, 2)
    cv2.imshow('Security & Posture', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

video_capture.release()
cv2.destroyAllWindows()