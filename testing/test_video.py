import cv2
import numpy as np
import os

OUTPUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "test_3x3.avi"
)

WIDTH = 3
HEIGHT = 3
FPS = 3

# MJPEG dentro de AVI
fourcc = cv2.VideoWriter_fourcc(*"MJPG")
video = cv2.VideoWriter(
    OUTPUT,
    fourcc,
    FPS,
    (WIDTH, HEIGHT)
)

if not video.isOpened():
    raise RuntimeError("No se pudo crear el video.")

# OpenCV usa BGR
red = np.full((HEIGHT, WIDTH, 3), (0, 0, 255), dtype=np.uint8)
blue = np.full((HEIGHT, WIDTH, 3), (255, 0, 0), dtype=np.uint8)
green = np.full((HEIGHT, WIDTH, 3), (0, 255, 0), dtype=np.uint8)

# 3 frames rojos
for _ in range(3):
    video.write(red)

# 3 frames azules
for _ in range(3):
    video.write(blue)

# 3 frames verdes
for _ in range(3):
    video.write(green)

video.release()

print(f"Video generado: {OUTPUT}")
print("Resolución: 3x3")
print("Frames: 9")
print("FPS: 3")
print("Secuencia: 🔴 🔴 🔴 → 🔵 🔵 🔵 → 🟢 🟢 🟢")

# Abrir automáticamente
os.startfile(OUTPUT)
