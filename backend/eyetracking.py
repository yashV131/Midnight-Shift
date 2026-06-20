# eyetracking.py
import cv2
import dlib
import time
import requests
import threading
import os
import urllib.request


# Resolve predictor path relative to this module so it works when app
# is launched from the project root.
HERE = os.path.dirname(__file__)
PREDICTOR_PATH = os.path.join(HERE, "shape_predictor_68_face_landmarks.dat")
PREDICTOR_URL = "https://raw.githubusercontent.com/italojs/facial-landmarks-recognition/master/shape_predictor_68_face_landmarks.dat"

def ensure_predictor():
    if not os.path.exists(PREDICTOR_PATH):
        print("Downloading face landmark predictor...")
        urllib.request.urlretrieve(PREDICTOR_URL, PREDICTOR_PATH)
        print("Predictor downloaded.")

class EyeTracker:
    def __init__(self, stop_event, predictor_path=PREDICTOR_PATH):
        self.stop_event = stop_event
        self.predictor_path = predictor_path
        self.api_url = "http://127.0.0.1:5000/api/eye-tracking/update"
        
        # Ensure predictor file exists (downloads if missing)
        try:
            ensure_predictor()
        except Exception as e:
            print(f"Warning: failed to download predictor automatically: {e}")

        self.detector = dlib.get_frontal_face_detector()
        try:
            self.predictor = dlib.shape_predictor(self.predictor_path)
        except Exception as e:
            raise FileNotFoundError(f"Predictor file not found at {self.predictor_path}. Please download it and place it in the backend folder. Original error: {e}")

        self.cap = cv2.VideoCapture(0)

    def _eye_aspect_ratio(self, eye):
        A = abs(eye[1].y - eye[5].y)
        B = abs(eye[2].y - eye[4].y)
        C = abs(eye[0].x - eye[3].x)
        return (A + B) / (2.0 * C + 1e-6)

    def _send_stats(self, stats):
        try:
            requests.post(self.api_url, json=stats, timeout=1)
        except requests.RequestException:
            pass

    def start_tracking(self):
        start_time = time.time()
        last_update_time = start_time
        blinks, eyes_open_frames, at_screen_frames, total_frames = 0, 0, 0, 0
        prev_eyes_open = True

        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret: break
            
            total_frames += 1
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detector(gray)
            is_looking_at_screen, are_eyes_open = False, False

            if faces:
                face = faces[0]
                landmarks = self.predictor(gray, face)
                left_eye = [landmarks.part(i) for i in range(36, 42)]
                right_eye = [landmarks.part(i) for i in range(42, 48)]
                ear = (self._eye_aspect_ratio(left_eye) + self._eye_aspect_ratio(right_eye)) / 2.0
                if ear > 0.25: are_eyes_open = True
                
                face_center_x = face.center().x
                if frame.shape[1] * 0.2 < face_center_x < frame.shape[1] * 0.8:
                    is_looking_at_screen = True

            if are_eyes_open:
                eyes_open_frames += 1
                if not prev_eyes_open: blinks += 1
            prev_eyes_open = are_eyes_open
            
            if is_looking_at_screen: at_screen_frames += 1

            if time.time() - last_update_time > 2:
                total_duration = time.time() - start_time
                productive_time = (at_screen_frames / total_frames) * total_duration if total_frames > 0 else 0
                self._send_stats({
                    'blinks': blinks,
                    'eyes_open': (eyes_open_frames / total_frames * 100) if total_frames > 0 else 0,
                    'looking_at_screen': (at_screen_frames / total_frames * 100) if total_frames > 0 else 0,
                    'productive_time': productive_time
                })
                last_update_time = time.time()
            time.sleep(1/30)
            
        self.cap.release()
        print("EyeTracker stopped.")