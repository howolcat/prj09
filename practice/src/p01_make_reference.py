from pathlib import Path

import cv2


# --------------------------------------------------
# 1. 경로 설정
#    이 파일 위치: practice/src/p01_make_reference.py
#    parent        → practice/src
#    parent.parent → practice  (실습 기준 폴더)
#    → 프로젝트 어디에서 실행해도 practice 폴더를 기준으로 동작합니다.
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = BASE_DIR / "samples" / "raw"              # 휴대폰 원본 사진
REFERENCE_DIR = BASE_DIR / "samples" / "reference"  # 잘라낸 기준 ROI
PREVIEW_DIR = BASE_DIR / "outputs" / "p01_reference"

REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. 작업 크기 설정
#    휴대폰 원본(3000×4000)은 너무 크므로
#    IP Webcam 640×480과 비슷한 480×640(세로)으로 줄여서 사용합니다.
# --------------------------------------------------
WORK_SIZE = (480, 640)   # cv2.resize는 (가로, 세로) 순서


# --------------------------------------------------
# 3. 이미지별 ROI 좌표 (480×640 기준)
#    두 사진은 충전기 위치가 달라서 ROI를 따로 지정합니다.
#    대신 크기는 160×160으로 똑같이 맞추고,
#    "충전기 윗면 중앙"을 기준으로 같은 위치 관계가 되도록 잡았습니다.
#      - 위쪽 80px : 케이블이 꽂히는 영역
#      - 아래쪽 80px: 충전기 몸통
# --------------------------------------------------
ROI_SIZE = 160

ROI_SETTINGS = {
    # 이름: (원본 파일명, 충전기 윗면 중앙 x, 충전기 윗면 y)
    "ok": ("ok_raw.png", 270, 287),   # 케이블 꽂힘
    "ng": ("ng_raw.png", 272, 227),   # 케이블 없음
}


def make_roi_box(center_x, top_y, width, height):
    """충전기 윗면 중앙을 기준으로 ROI 사각형 좌표를 계산합니다."""
    half = ROI_SIZE // 2

    x1 = center_x - half
    y1 = top_y - half          # 윗면보다 80px 위에서 시작
    x2 = x1 + ROI_SIZE
    y2 = y1 + ROI_SIZE

    # 좌표가 이미지 밖으로 나가지 않게 제한 (1일차 방식)
    x1 = max(0, min(x1, width))
    x2 = max(0, min(x2, width))
    y1 = max(0, min(y1, height))
    y2 = max(0, min(y2, height))

    if x1 >= x2 or y1 >= y2:
        raise ValueError(f"잘못된 ROI 좌표: {(x1, y1, x2, y2)}")

    return x1, y1, x2, y2


# --------------------------------------------------
# 4. 원본 읽기 → 축소 → ROI 자르기 → 저장
# --------------------------------------------------
for label, (file_name, center_x, top_y) in ROI_SETTINGS.items():

    raw_path = RAW_DIR / file_name
    image = cv2.imread(str(raw_path))

    if image is None:
        raise FileNotFoundError(f"원본 이미지를 읽지 못했습니다: {raw_path}")

    # 3000×4000 → 480×640
    small = cv2.resize(image, WORK_SIZE, interpolation=cv2.INTER_AREA)
    height, width = small.shape[:2]

    x1, y1, x2, y2 = make_roi_box(center_x, top_y, width, height)

    # NumPy 슬라이싱은 [y, x] 순서
    roi = small[y1:y2, x1:x2]

    roi_path = REFERENCE_DIR / f"{label}.jpg"
    cv2.imwrite(str(roi_path), roi)

    # 원본에서 어디를 잘랐는지 확인용 Preview
    preview = small.copy()
    cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.imwrite(str(PREVIEW_DIR / f"{label}_preview.jpg"), preview)

    print(f"[{label}] ROI={(x1, y1, x2, y2)} 크기={roi.shape} → {roi_path.name}")

print("기준 ROI 생성 완료")
