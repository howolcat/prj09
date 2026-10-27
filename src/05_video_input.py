from pathlib import Path

import cv2


video_path = Path("samples/sample.mp4")
output_dir = Path("outputs/frames")
output_dir.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(str(video_path))

if not cap.isOpened():
    raise RuntimeError(
        f"영상을 열 수 없습니다: {video_path}"
    )

fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print("영상 :", video_path)
print("FPS  :", fps)
print("크기 :", width, "x", height)

frame_count = 0
saved_count = 0

while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame_count += 1

    # 약 30 Frame마다 한 장 저장하는 예제
    if frame_count % 30 == 0:
        output_path = (
            output_dir / f"frame_{frame_count:05d}.jpg"
        )

        cv2.imwrite(str(output_path), frame)
        saved_count += 1

        print("저장:", output_path.name)

cap.release()

print("전체 Frame:", frame_count)
print("저장 Frame:", saved_count)