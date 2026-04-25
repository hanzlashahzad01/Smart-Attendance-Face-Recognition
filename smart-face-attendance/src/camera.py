import cv2
import os
from dotenv import load_dotenv

load_dotenv()

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))

class Camera:
    def __init__(self, index=CAMERA_INDEX):
        self.index = index
        self.cap = None

    def start(self):
        self.cap = cv2.VideoCapture(self.index)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open camera {self.index}")

    def get_frame(self):
        if self.cap is None:
            raise RuntimeError("Camera is not started")
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def stop(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None
