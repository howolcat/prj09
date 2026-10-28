"""
l02_make_reference.py — Reference 원본에서 '찾을 로고'만 잘라 기준 이미지를 만듭니다.

4일차 24_day04_prepare.py와 같은 역할입니다.
단, 4일차에서 겪은 문제(issue: Template이 이미지 바닥에 닿아 shift에서 실패)를
다시 겪지 않도록, 잘라낸 영역이 이미지 가장자리에 너무 가까우면 경고합니다.

실행 (프로젝트 최상위에서):
    # 마우스로 로고 영역을 드래그 → Enter (취소: c)
    python practice_label/src/l02_make_reference.py

    # 좌표를 직접 지정 (다시 실행해도 같은 결과 → 재현 가능)
    python practice_label/src/l02_make_reference.py --roi 200 150 440 300

결과:
    samples/reference/reference.jpg        ← 찾을 로고 (Template)
    samples/reference/reference_preview.jpg ← 원본에 초록 사각형 표시
    configs/reference_roi.json             ← 사용한 좌표 기록
"""

import argparse
import json
from pathlib import Path

import cv2


BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_DIR = BASE_DIR / "samples" / "reference"
CONFIG_PATH = BASE_DIR / "configs" / "reference_roi.json"

MIN_EDGE_MARGIN = 30      # 로고 영역이 가장자리에서 최소 이만큼(px) 떨어져 있어야 함
MIN_ROI_SIZE = 40         # 너무 작은 로고는 특징점이 부족함


# --------------------------------------------------
# 1. 가장 최근에 찍은 Reference 원본 찾기
#    reference_full_001.jpg, _002.jpg ... 중 마지막 번호 사용
# --------------------------------------------------
def find_reference_full():
    candidates = sorted(REFERENCE_DIR.glob("reference_full_*.jpg"))
    if not candidates:
        raise FileNotFoundError(
            "Reference 원본이 없습니다. l01_capture.py에서 r 키로 먼저 저장하세요."
        )
    return candidates[-1]


# --------------------------------------------------
# 2. 로고 영역 고르기 (마우스 또는 --roi 좌표)
# --------------------------------------------------
def select_roi_by_mouse(image):
    print("로고 영역을 드래그한 뒤 Enter/Space, 취소는 c")
    x, y, w, h = cv2.selectROI("select logo", image, showCrosshair=True)
    cv2.destroyAllWindows()
    if w == 0 or h == 0:
        raise SystemExit("선택을 취소했습니다.")
    return x, y, x + w, y + h


# --------------------------------------------------
# 3. 좌표 검사: 크기 + 가장자리 여유
#    가장자리에 붙어 있으면 제품이 조금만 움직여도
#    로고 일부가 화면 밖으로 나가 Matching이 실패할 수 있습니다.
# --------------------------------------------------
def check_roi(x1, y1, x2, y2, width, height):
    if x2 - x1 < MIN_ROI_SIZE or y2 - y1 < MIN_ROI_SIZE:
        raise ValueError(f"로고 영역이 너무 작습니다: {x2 - x1}x{y2 - y1}px")

    margins = {
        "왼쪽": x1, "위": y1, "오른쪽": width - x2, "아래": height - y2,
    }
    warnings = [f"{side} {gap}px" for side, gap in margins.items() if gap < MIN_EDGE_MARGIN]
    return margins, warnings


def main():
    parser = argparse.ArgumentParser(description="Reference 로고 자르기")
    parser.add_argument("--roi", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"),
                        help="로고 영역 좌표 (생략하면 마우스로 선택)")
    args = parser.parse_args()

    source_path = find_reference_full()
    image = cv2.imread(str(source_path))
    if image is None:
        raise FileNotFoundError(source_path)
    height, width = image.shape[:2]

    if args.roi:
        x1, y1, x2, y2 = args.roi
    else:
        x1, y1, x2, y2 = select_roi_by_mouse(image)

    # 이미지 밖 좌표는 안쪽으로 맞춤
    x1, x2 = sorted((max(0, min(x1, width)), max(0, min(x2, width))))
    y1, y2 = sorted((max(0, min(y1, height)), max(0, min(y2, height))))

    margins, warnings = check_roi(x1, y1, x2, y2, width, height)

    # --------------------------------------------------
    # 4. 저장: 로고 / 미리보기 / 좌표 기록
    # --------------------------------------------------
    reference = image[y1:y2, x1:x2]
    cv2.imwrite(str(REFERENCE_DIR / "reference.jpg"), reference)

    preview = image.copy()
    color = (0, 0, 255) if warnings else (0, 255, 0)     # 경고가 있으면 빨간 사각형
    cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
    cv2.imwrite(str(REFERENCE_DIR / "reference_preview.jpg"), preview)

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps({
        "source": source_path.name,
        "source_size": [width, height],
        "roi": [x1, y1, x2, y2],
        "roi_size": [x2 - x1, y2 - y1],
        "edge_margin": margins,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print("원본      :", source_path.name, f"({width}x{height})")
    print("로고 영역 :", (x1, y1, x2, y2), f"→ {x2 - x1}x{y2 - y1}px")
    print("가장자리  :", ", ".join(f"{k} {v}px" for k, v in margins.items()))
    if warnings:
        print(f"⚠ 가장자리와 너무 가깝습니다({MIN_EDGE_MARGIN}px 미만): {', '.join(warnings)}")
        print("  → 제품을 화면 안쪽으로 옮겨 Reference를 다시 찍는 것을 추천합니다.")
    print("저장      : samples/reference/reference.jpg, reference_preview.jpg")
    print("좌표 기록 :", CONFIG_PATH.relative_to(BASE_DIR))


if __name__ == "__main__":
    main()
