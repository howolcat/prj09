from pathlib import Path

import cv2


image_path = Path("samples/day02/cap_on_reference.jpg")
output_dir = Path("outputs/day02/color")
output_dir.mkdir(parents=True, exist_ok=True)

image = cv2.imread(str(image_path))

if image is None:
    raise FileNotFoundError(
        f"이미지를 읽지 못했습니다: {image_path}"
    )

gray = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2GRAY,
)

hsv = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2HSV,
)

h, s, v = cv2.split(hsv)

cv2.imwrite(
    str(output_dir / "original_bgr.jpg"),
    image,
)

cv2.imwrite(
    str(output_dir / "gray.jpg"),
    gray,
)

cv2.imwrite(
    str(output_dir / "h_channel.jpg"),
    h,
)

cv2.imwrite(
    str(output_dir / "s_channel.jpg"),
    s,
)

cv2.imwrite(
    str(output_dir / "v_channel.jpg"),
    v,
)

print("입력 :", image_path)
print("저장 :", output_dir)
print("Color Space 결과 저장 완료")