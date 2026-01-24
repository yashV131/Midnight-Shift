import cv2
import time
import os
import numpy as np
from datetime import datetime

# Load pre-trained cascade classifiers
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

def lock_screen(reason=""):
    """Lock the Windows laptop"""
    try:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Screen locked - {reason}")
    except Exception as e:
        print(f"Error locking screen: {e}")

def calculate_head_pose(gray, face, eyes):
    """Calculate face orientation by analyzing eye positions"""
    x, y, w, h = face
    face_center_x = x + w // 2
    
    if len(eyes) >= 2:
        # Sort eyes by x position (left and right)
        eyes_sorted = sorted(eyes, key=lambda e: e[0])
        left_eye = eyes_sorted[0]
        right_eye = eyes_sorted[1]
        
        left_eye_center = left_eye[0] + left_eye[2] // 2
        right_eye_center = right_eye[0] + right_eye[2] // 2
        
        eyes_center_x = (left_eye_center + right_eye_center) / 2
        
        # Calculate yaw (how much face is turned left-right)
        # If eyes are centered in face = 0°, if shifted = rotated
        eye_offset = eyes_center_x - face_center_x
        yaw = (eye_offset / (w / 2)) * 45  # Scale to degrees
        
        # Calculate pitch based on eye vertical position in face
        eye_y_avg = (left_eye[1] + right_eye[1]) / 2
        y_offset = eye_y_avg - (y + h // 3)
        pitch = (y_offset / h) * 30
        
    else:
        yaw = 0
        pitch = 0
    
    return yaw, pitch, 0

def detect_face_and_orientation():
    """Detect face and head pose orientation including profiles"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Cannot access webcam")
        return False, False, 0, 0, 0, None
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Error: Cannot read from webcam")
        return False, False, 0, 0, 0, None
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect frontal faces
    frontal_faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    # Detect profile faces (left and right)
    profile_faces = profile_cascade.detectMultiScale(gray, 1.3, 5)
    
    # Check if any face detected
    if len(frontal_faces) == 0 and len(profile_faces) == 0:
        cv2.putText(frame, "NO FACE DETECTED", (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        return False, False, 0, 0, 0, frame
    
    # Determine which face to use (prefer frontal)
    if len(frontal_faces) > 0:
        face = frontal_faces[0]
        face_type = "FRONTAL"
        is_profile = False
    else:
        face = profile_faces[0]
        face_type = "PROFILE"
        is_profile = True
    
    x, y, w, h = face
    
    # Draw face rectangle
    color = (0, 255, 0) if not is_profile else (255, 165, 0)  # Green for frontal, orange for profile
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    
    # Detect eyes in face region
    roi_gray = gray[y:y + h, x:x + w]
    eyes = eye_cascade.detectMultiScale(roi_gray)
    
    # Draw eyes
    for (ex, ey, ew, eh) in eyes[:2]:  # Only first 2 eyes
        cv2.circle(frame, (x + ex + ew // 2, y + ey + eh // 2), 5, (255, 0, 0), 2)
    
    # Calculate head pose
    yaw, pitch, roll = calculate_head_pose(gray, face, [(x + e[0], y + e[1], e[2], e[3]) for e in eyes[:2]])
    
    # Configuration thresholds
    YAW_THRESHOLD = 20      # Max rotation left-right
    PITCH_THRESHOLD = 15    # Max rotation up-down
    
    # If profile detected, allow it (don't lock out)
    if is_profile:
        yaw = 0  # Reset yaw to indicate acceptable position
        is_facing_forward = True  # Allow side profiles
    else:
        # Check if facing forward (for frontal faces only)
        is_facing_forward = (
            abs(yaw) < YAW_THRESHOLD and 
            abs(pitch) < PITCH_THRESHOLD
        )
    
    # Draw head pose info
    y_offset = 40
    cv2.putText(frame, f"Face Type: {face_type}", (10, y_offset - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 255), 2)
    cv2.putText(frame, f"Yaw: {yaw:.1f}° (L-R Turn)", (10, y_offset), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    cv2.putText(frame, f"Pitch: {pitch:.1f}° (U-D Tilt)", (10, y_offset + 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    # Draw status indicator
    h_frame = frame.shape[0]
    if is_facing_forward:
        if is_profile:
            status = "SIDE PROFILE - OK"
        else:
            status = "FACING FORWARD - OK"
        status_color = (0, 255, 0)  # Green
    else:
        status = "FACE TURNED AWAY"
        status_color = (0, 0, 255)  # Red
    
    cv2.putText(frame, status, (10, h_frame - 20), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.2, status_color, 3)
    
    return True, is_facing_forward, yaw, pitch, roll, frame

def main():
    """Main loop to monitor face presence and orientation"""
    no_face_duration = 0
    turned_away_duration = 0
    NO_FACE_TIMEOUT = 10        # Lock after 10 seconds of no face
    TURNED_AWAY_TIMEOUT = 8     # Lock after 8 seconds of turned away
    CHECK_INTERVAL = 1
    
    print("=" * 60)
    print("FACE-DETECTION AUTO-LOCK SYSTEM")
    print("=" * 60)
    print("Features:")
    print("  - Detects if you're looking away (face turned sideways)")
    print("  - Locks if no face detected for 10 seconds")
    print("  - Locks if face turned away for 8 seconds")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        while True:
            face_detected, facing_forward, yaw, pitch, roll, frame = detect_face_and_orientation()
            
            # Display camera feed
            if frame is not None:
                cv2.imshow("Face Detection - Auto Lock", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            if not face_detected:
                no_face_duration += CHECK_INTERVAL
                turned_away_duration = 0
                status = f"NO FACE DETECTED ({no_face_duration:.0f}s / {NO_FACE_TIMEOUT}s)"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status}")
                
                if no_face_duration >= NO_FACE_TIMEOUT:
                    lock_screen("No face detected")
                    no_face_duration = 0
                    time.sleep(5)
            
            elif not facing_forward:
                turned_away_duration += CHECK_INTERVAL
                no_face_duration = 0
                status = f"FACE TURNED AWAY (Yaw: {yaw:.1f}°, Pitch: {pitch:.1f}°) - {turned_away_duration:.0f}s / {TURNED_AWAY_TIMEOUT}s"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status}")
                
                if turned_away_duration >= TURNED_AWAY_TIMEOUT:
                    lock_screen("Face turned away")
                    turned_away_duration = 0
                    time.sleep(5)
            
            else:
                no_face_duration = 0
                turned_away_duration = 0
                status = f"FACING FORWARD ✓ (Yaw: {yaw:.1f}°, Pitch: {pitch:.1f}°)"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {status}")
            
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nAuto-lock system stopped")
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

