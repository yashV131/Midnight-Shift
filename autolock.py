import cv2
import time
import subprocess
import os
from datetime import datetime

# Initialize the face detector using OpenCV's pre-trained cascade classifier
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)

def lock_screen():
    """Lock the Windows laptop"""
    try:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Screen locked due to no face detected")
    except Exception as e:
        print(f"Error locking screen: {e}")

def detect_face():
    """Detect face using webcam"""
    cap = cv2.VideoCapture(0)  # 0 is the default webcam
    
    if not cap.isOpened():
        print("Error: Cannot access webcam")
        return False
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("Error: Cannot read from webcam")
        return False
    
    # Convert to grayscale for better detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(30, 30)
    )
    
    return len(faces) > 0

def main():
    """Main loop to monitor face presence"""
    no_face_duration = 0
    NO_FACE_TIMEOUT = 10  # Lock after 10 seconds of no face detected
    CHECK_INTERVAL = 2    # Check every 2 seconds
    
    print("Auto-lock system started")
    print(f"System will lock if no face is detected for {NO_FACE_TIMEOUT} seconds")
    print("Press Ctrl+C to stop the program\n")
    
    try:
        while True:
            if detect_face():
                no_face_duration = 0
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Face detected - System active")
            else:
                no_face_duration += CHECK_INTERVAL
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No face detected ({no_face_duration}s)")
                
                if no_face_duration >= NO_FACE_TIMEOUT:
                    lock_screen()
                    no_face_duration = 0  # Reset counter after locking
                    time.sleep(5)  # Wait a bit before checking again
            
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nAuto-lock system stopped")
        cap = cv2.VideoCapture(0)
        cap.release()

if __name__ == "__main__":
    main()

