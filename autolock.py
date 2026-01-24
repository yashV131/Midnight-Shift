import cv2
import time
import os
import numpy as np
from datetime import datetime

# Load pre-trained cascade classifiers
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')

def lock_screen(reason=""):
    """Lock the Windows laptop"""
    try:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Screen locked - {reason}")
    except Exception as e:
        print(f"Error locking screen: {e}")

def detect_face():
    """Detect if face is present in frame (frontal or profile)"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Cannot access webcam")
        return False, None
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Error: Cannot read from webcam")
        return False, None
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect frontal faces
    frontal_faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    # Detect profile faces (side view)
    profile_faces = profile_cascade.detectMultiScale(gray, 1.3, 5)
    
    # Check if any face detected
    if len(frontal_faces) == 0 and len(profile_faces) == 0:
        cv2.putText(frame, "NO FACE DETECTED", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        return False, frame
    
    # Draw frontal faces
    for (x, y, w, h) in frontal_faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(frame, "Frontal", (x, y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    # Draw profile faces
    for (x, y, w, h) in profile_faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 165, 0), 2)
        cv2.putText(frame, "Profile", (x, y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
    
    # Draw status indicator
    h_frame = frame.shape[0]
    if len(frontal_faces) > 0:
        status = f"FRONTAL FACE DETECTED ✓"
    else:
        status = f"PROFILE DETECTED ✓"
    cv2.putText(frame, status, (10, h_frame - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
    
    return True, frame

def main():
    """Main loop to monitor face presence"""
    no_face_duration = 0
    NO_FACE_TIMEOUT = 10  # Lock after 10 seconds of no face
    CHECK_INTERVAL = 1
    
    print("=" * 60)
    print("FACE-DETECTION AUTO-LOCK SYSTEM")
    print("=" * 60)
    print(f"No face timeout: {NO_FACE_TIMEOUT}s")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            face_detected, frame = detect_face()
            
            # Display camera feed
            if frame is not None:
                cv2.imshow("Face Detection - Auto Lock", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            if face_detected:
                no_face_duration = 0
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Face detected - System active ✓")
            else:
                no_face_duration += CHECK_INTERVAL
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No face detected ({no_face_duration:.0f}s / {NO_FACE_TIMEOUT}s)")
                
                if no_face_duration >= NO_FACE_TIMEOUT:
                    lock_screen("No face detected")
                    no_face_duration = 0
                    time.sleep(5)
            
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nAuto-lock system stopped")
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

