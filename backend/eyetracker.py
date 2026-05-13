#CURRENT WORKING VERSION
import cv2
import dlib
import time
import ctypes

# ---------------- CONFIG ----------------
DISTRACTION_SECONDS = 10
BREAK_MINUTES = 20
BREAK_SECONDS = BREAK_MINUTES * 60
FRAME_RATE = 30
LOOK_AWAY_THRESHOLD = 0.25
SIDE_FACE_NOSE_RATIO = 0.35
EYE_CLOSED_THRESHOLD = 2       # seconds for long closure
PREDICTOR_PATH = r"C:/Users/ayala/OneDrive/Documents/tamuhack/shape_predictor_68_face_landmarks.dat"
# ---------------------------------------

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(PREDICTOR_PATH)

productive_time = 0.0
total_blinks = 0
productive_start_time = None
prev_eyes_open = True
eye_closed_start_time = None

last_facing_time = time.time()
last_focus_time = time.time()
timer_paused = False

# ---------------- SESSION SETUP ----------------
mode = input("Choose session type: (1) Timer, (2) Stopwatch: ")
if mode == "1":
    session_minutes = float(input("Enter session time in minutes: "))
    session_seconds = session_minutes * 60
else:
    session_seconds = None

cap = cv2.VideoCapture(0)
start_time = time.time()

# ---------------- FUNCTIONS ----------------
def send_notification(title, message):
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40 | 0x1)

def eye_aspect_ratio(eye):
    top = eye[1].y - eye[5].y
    bottom = eye[2].y - eye[4].y
    horizontal = eye[0].x - eye[3].x
    return (abs(top) + abs(bottom)) / (2 * abs(horizontal) + 1e-6)

def is_eye_open(eye):
    return eye_aspect_ratio(eye) > 0.2

def face_center(face):
    return (face.left() + face.width() // 2, face.top() + face.height() // 2)

print("Press Q to quit")

# ---------------- MAIN LOOP ----------------
while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)

    looking_at_screen = False
    side_profile = False
    both_eyes_open = False

    for face in faces:
        landmarks = predictor(gray, face)
        left_eye = [landmarks.part(i) for i in range(36, 42)]
        right_eye = [landmarks.part(i) for i in range(42, 48)]
        nose = landmarks.part(30)

        left_open = is_eye_open(left_eye)
        right_open = is_eye_open(right_eye)
        both_eyes_open = left_open and right_open

        # Side profile detection
        if left_open != right_open:
            side_profile = True

        eye_center_x = (left_eye[0].x + right_eye[3].x) / 2
        nose_offset = abs(nose.x - eye_center_x) / face.width()
        if nose_offset > SIDE_FACE_NOSE_RATIO:
            side_profile = True

        fx, fy = face_center(face)
        h, w = frame.shape[:2]
        centered = (w*LOOK_AWAY_THRESHOLD < fx < w*(1-LOOK_AWAY_THRESHOLD) and
                    h*LOOK_AWAY_THRESHOLD < fy < h*(1-LOOK_AWAY_THRESHOLD))
        if centered and not side_profile:
            looking_at_screen = True
            last_facing_time = time.time()

        # Draw face rectangle
        color = (0, 255, 0) if looking_at_screen else (0, 0, 255)
        cv2.rectangle(frame, (face.left(), face.top()), (face.right(), face.bottom()), color, 2)

    # -------- EYE CLOSURE AND BLINK LOGIC --------
    if both_eyes_open:
        if eye_closed_start_time is not None:
            closed_duration = time.time() - eye_closed_start_time
            eye_closed_start_time = None
            if closed_duration <= EYE_CLOSED_THRESHOLD:
                total_blinks += 1  # count short blink
    else:
        if eye_closed_start_time is None:
            eye_closed_start_time = time.time()

    # -------- PRODUCTIVE TIME LOGIC --------
    timer_should_be_paused = (not looking_at_screen or side_profile or
                              (eye_closed_start_time is not None and time.time() - eye_closed_start_time > EYE_CLOSED_THRESHOLD))

    if timer_paused and not timer_should_be_paused:
        productive_start_time = time.time()
    elif not timer_paused and timer_should_be_paused:
        if productive_start_time is not None:
            productive_time += time.time() - productive_start_time
            productive_start_time = None
    timer_paused = timer_should_be_paused

    # -------- DISTRACTION ALERT --------
    if timer_paused and time.time() - last_facing_time >= DISTRACTION_SECONDS:
        send_notification("Attention Alert", "You may be getting distracted!")
        last_facing_time = time.time()

    # -------- EYE BREAK ALERT --------
    if not timer_paused:
        if time.time() - last_focus_time >= BREAK_SECONDS:
            send_notification("Eye Break", "Give your eyes a break!")
            last_focus_time = time.time()
    else:
        last_focus_time = time.time()

    # -------- DISPLAY --------
    display_productive_time = productive_time
    if productive_start_time is not None:
        display_productive_time += time.time() - productive_start_time

    elapsed = time.time() - start_time
    remaining = session_seconds - elapsed if session_seconds else elapsed

    cv2.putText(frame, f"Blinks: {total_blinks}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,0,0),2)
    cv2.putText(frame, f"Productive Time: {int(display_productive_time)}s", (10,60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0),2)
    cv2.putText(frame, f"Focused: {looking_at_screen}", (10,90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255),2)
    if session_seconds:
        cv2.putText(frame, f"Time Remaining: {int(remaining)}s", (10,120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0),2)

    cv2.imshow("Eye Tracking Productivity", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    if session_seconds and elapsed >= session_seconds:
        break

# Add final productive time if running
if productive_start_time is not None:
    productive_time += time.time() - productive_start_time

cap.release()
cv2.destroyAllWindows()

print("\n--- SESSION SUMMARY ---")
print(f"Productive time: {int(productive_time)}s")
print(f"Total blinks: {total_blinks}")
