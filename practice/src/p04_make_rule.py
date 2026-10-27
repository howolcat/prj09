from pathlib import Path
import json

import cv2

from cable_features import measure_features, FIXED_THRESHOLD


# --------------------------------------------------
# 1. 경로 설정
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

REFERENCE_DIR = BASE_DIR / "samples" / "reference"
RULE_PATH = BASE_DIR / "configs" / "cable_rule.json"
RULE_PATH.parent.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. 사용할 측정 방법
#    p03 결과: otsu는 NG 면적이 OK보다 커서 방향이 거꾸로 나옴
#              fixed는 OK > NG로 정상 구분
#    → 이번 Rule은 fixed 방식을 사용합니다.
# --------------------------------------------------
METHOD = "fixed"


def read_reference(label):
    path = REFERENCE_DIR / f"{label}.jpg"
    image = cv2.imread(str(path))
    if image is None:
        raise FileNotFoundError(f"p01을 먼저 실행하세요: {path}")
    return image


# --------------------------------------------------
# 3. 기준 이미지 2장 측정 (3일차 21번과 같은 흐름)
# --------------------------------------------------
ok_features, *_ = measure_features(read_reference("ok"), METHOD)
ng_features, *_ = measure_features(read_reference("ng"), METHOD)

ok_ratio = ok_features["largest_area_ratio"]
ng_ratio = ng_features["largest_area_ratio"]


# --------------------------------------------------
# 4. 후보 기준값 = 두 측정값의 중간값
#    방향 확인: 케이블이 있을 때 면적이 더 커야 정상
# --------------------------------------------------
if ok_ratio == ng_ratio:
    raise RuntimeError("OK와 NG 측정값이 같아서 이 Feature로는 구분할 수 없습니다.")

candidate_threshold = (ok_ratio + ng_ratio) / 2.0
ok_when_greater = ok_ratio > ng_ratio


# --------------------------------------------------
# 5. Rule을 JSON으로 저장 (5일차 Rule Freeze 방식)
#    → p05는 이 파일만 읽어서 판정합니다.
#      테스트 결과를 보고 기준값을 다시 바꾸지 않기 위해서입니다.
# --------------------------------------------------
rule = {
    "rule_version": "cable-v1.0",
    "method": METHOD,
    "fixed_threshold": FIXED_THRESHOLD,
    "feature": "largest_area_ratio",
    "ok_reference_ratio": ok_ratio,
    "ng_reference_ratio": ng_ratio,
    "area_ratio_threshold": candidate_threshold,
    "ok_when_greater": ok_when_greater,
}

RULE_PATH.write_text(
    json.dumps(rule, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("ok  ratio :", round(ok_ratio, 4))
print("ng  ratio :", round(ng_ratio, 4))
print("gap       :", round(abs(ok_ratio - ng_ratio), 4))
print("threshold :", round(candidate_threshold, 4))
print("OK 조건   :", "area_ratio >= threshold" if ok_when_greater
      else "area_ratio <= threshold")
print("Rule 저장 :", RULE_PATH)
