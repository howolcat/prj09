from pathlib import Path
import csv

import cv2
import numpy as np

from cable_features import measure_features, FIXED_THRESHOLD


# --------------------------------------------------
# 1. 경로 설정
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

REFERENCE_DIR = BASE_DIR / "samples" / "reference"
OUTPUT_DIR = BASE_DIR / "outputs" / "p03_feature"
REPORT_PATH = BASE_DIR / "reports" / "p03_reference_features.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. 이 파일의 목적
#    같은 ok / ng 이미지를 두 가지 Threshold 방법으로 측정해서
#    "어느 방법이 케이블 유무를 더 잘 구분하는가?"를 숫자로 비교합니다.
#
#      otsu  : 3일차 교재 방식 (자동 기준값)
#      fixed : 고정 기준값 FIXED_THRESHOLD
#
#    → Rule을 만들기 전에 측정부터! (3일차 핵심 사고방식)
# --------------------------------------------------
rows = []
views = []

for label in ["ok", "ng"]:

    image = cv2.imread(str(REFERENCE_DIR / f"{label}.jpg"))
    if image is None:
        raise FileNotFoundError(f"p01을 먼저 실행하세요: {label}.jpg")

    for method in ["otsu", "fixed"]:

        features, binary, cleaned, largest = measure_features(image, method)

        rows.append({"label": label, **features})

        # 결과 확인용: 원본 위에 가장 큰 Contour를 초록색으로 표시
        annotated = image.copy()
        if largest is not None:
            cv2.drawContours(annotated, [largest], -1, (0, 255, 0), 2)

        cleaned_bgr = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)
        title = f"{label}/{method} {features['largest_area_ratio']:.3f}"
        cv2.putText(cleaned_bgr, title, (4, 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        views.append(np.vstack([annotated, cleaned_bgr]))

        print(
            f"{label:3s} | {method:5s} | "
            f"threshold={features['threshold']:6.1f} | "
            f"area_ratio={features['largest_area_ratio']:.3f} | "
            f"count={features['valid_count']} | "
            f"border={features['touches_border']} | "
            f"gray_min={features['gray_min']:.0f}"
        )


# --------------------------------------------------
# 3. CSV 저장 + 비교 이미지 저장
#    비교 이미지 순서: ok/otsu, ok/fixed, ng/otsu, ng/fixed
# --------------------------------------------------
with REPORT_PATH.open("w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

cv2.imwrite(str(OUTPUT_DIR / "method_compare.png"), np.hstack(views))


# --------------------------------------------------
# 4. 방법별 OK / NG 차이(Gap) 요약
#    Gap이 크고, OK가 NG보다 커야 "케이블 있음 = 면적 큼" Rule이 성립합니다.
# --------------------------------------------------
print()
for method in ["otsu", "fixed"]:
    ok_ratio = next(r["largest_area_ratio"] for r in rows
                    if r["label"] == "ok" and r["method"] == method)
    ng_ratio = next(r["largest_area_ratio"] for r in rows
                    if r["label"] == "ng" and r["method"] == method)
    direction = "OK > NG (정상)" if ok_ratio > ng_ratio else "OK <= NG (거꾸로!)"
    print(f"{method:5s}: ok={ok_ratio:.3f}  ng={ng_ratio:.3f}  "
          f"gap={abs(ok_ratio - ng_ratio):.3f}  → {direction}")

print()
print("FIXED_THRESHOLD =", FIXED_THRESHOLD)
print("CSV :", REPORT_PATH)
print("이미지:", OUTPUT_DIR / "method_compare.png")
