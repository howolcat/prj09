from pathlib import Path

import cv2


image_path = Path("samples/sample01.jpg")
image = cv2.imread(str(image_path))

if image is None:
    raise FileNotFoundError(image_path)

height, width, channels = image.shape

print("파일명   :", image_path.name)
print("Width    :", width)
print("Height   :", height)
print("Channels :", channels)
print("Shape    :", image.shape)
print("DataType :", image.dtype)