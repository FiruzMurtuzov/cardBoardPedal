import cv2
import numpy as np
import subprocess

# --- Config ---
CAMERA_URL = 0 #It will use default webcam, change it to the link of your IP camera if needed 

#Boundry colours in HSV space for the pedal marker (I used greenish sticker (which were card board from scraped from razor box))
LOWER_COLOR = np.array([28, 100, 100])
UPPER_COLOR = np.array([45, 255, 255])  

# ydotool key codes for arrow keys
KEY_MAP = {
    "Up":    "103",
    "Down":  "108",
    "Left":  "105",
    "Right": "106",
}

# --- Key control ---
keys_held = set()

def press(key):
    if key not in keys_held:
        subprocess.run(["ydotool", "key", KEY_MAP[key] + ":1"])
        keys_held.add(key)

def release(key):
    if key in keys_held:
        subprocess.run(["ydotool", "key", KEY_MAP[key] + ":0"])
        keys_held.discard(key)

def release_all():
    for key in list(keys_held):
        release(key)

#Angle detection using fitLine, returns angle in degrees and the line vector and center point
def get_angle(contour):
    if len(contour) < 5:
        return 0, None, None
    output = cv2.fitLine(contour, cv2.DIST_L2, 0, 0.01, 0.01)
    vx = output[0].item()
    vy = output[1].item()
    cx = int(output[2].item())
    cy = int(output[3].item())
    angle = abs(np.degrees(np.arctan2(vy, vx)))
    angle = min(angle, 180 - angle)
    return angle, (vx, vy), (cx, cy)

#Camera 
cap = cv2.VideoCapture(CAMERA_URL)

print("Make sure ydotoold is running: sudo ydotoold")
print("Press Q to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_COLOR, UPPER_COLOR)
    mask_bgr = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    

    angle = 0
    state = "idle"
    state_color = (180, 180, 180)

    if contours:
        largest = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest)

        if area > 200:
            angle, vec, center = get_angle(largest)

            cv2.drawContours(mask_bgr, [largest], -1, (0, 255, 255), 2)

            x, y, bw, bh = cv2.boundingRect(largest)
            cv2.rectangle(mask_bgr, (x, y), (x + bw, y + bh),
                          (255, 100, 0), 1)

            if vec and center:
                vx, vy = vec
                cx, cy = center
            #drawing line and center point on mask for visualization, nothing necessary for the control. 
                cv2.circle(mask_bgr, (cx, cy), 6, (0, 255, 0), -1)
                 
                scale = 80
                x1 = int(cx - vx * scale)
                y1 = int(cy - vy * scale)
                x2 = int(cx + vx * scale)
                y2 = int(cy + vy * scale)
                cv2.line(mask_bgr, (x1, y1), (x2, y2), (0, 180, 255), 2)

                cv2.line(mask_bgr, (cx - 60, cy), (cx + 60, cy),
                         (180, 180, 180), 1)

                cv2.ellipse(mask_bgr, (cx, cy), (40, 40), 0, 0,
                            int(angle), (0, 200, 255), 2)

                cv2.putText(mask_bgr, f"area: {int(area)}",
                            (x, max(y - 8, 12)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            (255, 255, 0), 1)

    # mapping angles to the keys. With this degrees and my setup it accelrates when i push and brakes when i lift of my feet. I usually would not put
    #brake but in the game i tested which is HexGL, brake is needed to be able to control it the way you would expect to work.
    if angle < 15:
        state = "idle"
        state_color = (180, 180, 180)
        release_all()
    elif angle < 45:
        state = "ACCELERATE"
        state_color = (0, 255, 100)
        press("Up")
        release("Down")
    else:
        state = "BRAKE"
        state_color = (0, 100, 255)
        press("Down")
        release("Up")



    # Putting text on feed, and processed version as thumbnail to the corner
    h, w = frame.shape[:2]
    thumb_h, thumb_w = 160, 213
    thumb = cv2.resize(mask_bgr, (thumb_w, thumb_h))
    frame[10:10+thumb_h, 10:10+thumb_w] = thumb
    cv2.rectangle(frame, (10, 10), (10+thumb_w, 10+thumb_h), (255,255,0), 1)
    cv2.putText(frame, f"Angle: {angle:.1f} deg", (10, thumb_h + 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame, state, (10, thumb_h + 66),
            cv2.FONT_HERSHEY_SIMPLEX, 1.1, state_color, 2)

    cv2.imshow("Pedal Cam", frame)


    if cv2.waitKey(1) & 0xFF == ord('q'):
        release_all()
        break

cap.release()
cv2.destroyAllWindows()
print("Stopped.")