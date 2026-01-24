import cv2
import face_recognition
import os
import sys

def lock_laptop():
    if sys.platform == "win32":
        os.system("rundll32.exe user32.dll,LockWorkStation")
    elif sys.platform == "darwin":
        os.system("pmset displaysleepnow")
    else:
        os.system("gnome-screensaver-command -l")

video_capture = cv2.VideoCapture(0)

# 1. Registration Phase
print("Registering Owner... Look at the camera and press 'S'")
owner_encoding = None
while True:
    ret, frame = video_capture.read()
    cv2.putText(frame, "Press 'S' to Register Owner", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.imshow('Registration', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('s'):
        encodings = face_recognition.face_encodings(frame)
        if len(encodings) > 0:
            owner_encoding = encodings[0]
            break
cv2.destroyWindow('Registration')

# 2. Monitoring Phase
try:
    while True:
        ret, frame = video_capture.read()
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        owner_present = False
        intruder_present = False

        # First pass: Check everyone in the frame
        for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
            matches = face_recognition.compare_faces([owner_encoding], encoding, tolerance=0.6)
            
            if True in matches:
                owner_present = True
                color, name = (0, 255, 0), "OWNER"
            else:
                intruder_present = True
                color, name = (0, 0, 255), "UNKNOWN"
            
            # Draw visual feedback
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow('Security Monitor', frame)

        # 3. Decision Logic
        # LOCK ONLY IF: Someone is there AND it is NOT the owner
        if intruder_present and not owner_present:
            print("Intruder detected and Owner is missing! Locking...")
            cv2.waitKey(500) 
            lock_laptop()
            break

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    video_capture.release()
    cv2.destroyAllWindows()