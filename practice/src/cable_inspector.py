"""
케이블 체결 검사 Service Core

FastAPI(api_server.py)는 "요청을 받고 결과를 돌려주는 역할"만 하고,
실제 검사는 이 파일이 담당합니다. (10일차 service_core.py와 같은 구조)

    이미지 + ROI  →  inspect_image()  →  결과 Dictionary
"""

import base64
import json
from pathlib import Path

import cv2
import numpy as np

import cable_features
from cable_features import measure_features


BASE_DIR = Path(__file__).resolve().parent.parent
RULE_PATH = BASE_DIR / "configs" / "cable_rule.json"

MIN_ROI_PIXELS = 20   # 가로·세로 20px보다 작은 ROI는 검사하지 않음


# --------------------------------------------------
# 1. p04에서 고정한 Rule 읽기
#    서비스는 Rule을 새로 계산하지 않고, 저장된 값만 사용합니다.
#    path를 주면 다른 Rule 파일(예: 웹캠용)도 읽을 수 있습니다.
# --------------------------------------------------
def load_rule(path=RULE_PATH):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"configs/{path.name}이 없습니다. Rule을 먼저 만들어 주세요."
        )

    rule = json.loads(path.read_text(encoding="utf-8"))

    # Rule을 만들 때와 같은 고정 Threshold로 측정하도록 맞춥니다.
    cable_features.FIXED_THRESHOLD = rule["fixed_threshold"]
    return rule


# --------------------------------------------------
# 2. 이미지 ↔ 문자열 변환
#    JSON에는 이미지(바이트)를 그대로 넣을 수 없어서
#    Base64 문자열로 바꿔서 주고받습니다.
# --------------------------------------------------
def decode_base64_image(data):
    """브라우저가 보낸 Base64(또는 data:image/...;base64,...)를 OpenCV 이미지로 변환"""
    if "," in data and data.strip().startswith("data:"):
        data = data.split(",", 1)[1]          # 앞의 "data:image/png;base64," 제거

    try:
        raw = base64.b64decode(data, validate=True)
    except ValueError as error:
        raise ValueError("Base64 이미지 형식이 올바르지 않습니다.") from error

    buffer = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("이미지를 읽지 못했습니다. jpg/png 파일인지 확인하세요.")
    return image


def encode_jpg_base64(image):
    """OpenCV 이미지를 브라우저 <img>에 바로 넣을 수 있는 문자열로 변환"""
    ok, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")


# --------------------------------------------------
# 3. ROI 자르기
#    roi는 0~1 사이 비율 좌표 {x1, y1, x2, y2}입니다.
#    (화면 크기가 달라도 같은 위치를 가리키도록 비율을 사용)
#    roi가 없으면 이미지 전체를 이미 잘라진 ROI로 봅니다. (3일차 방식)
# --------------------------------------------------
def crop_roi(image, roi):
    if roi is None:
        return image, None

    height, width = image.shape[:2]
    x1 = max(0, min(round(roi["x1"] * width), width))
    x2 = max(0, min(round(roi["x2"] * width), width))
    y1 = max(0, min(round(roi["y1"] * height), height))
    y2 = max(0, min(round(roi["y2"] * height), height))

    if x2 - x1 < MIN_ROI_PIXELS or y2 - y1 < MIN_ROI_PIXELS:
        raise ValueError("ROI가 너무 작습니다. 더 넓게 선택하세요.")

    return image[y1:y2, x1:x2], (x1, y1, x2, y2)


# --------------------------------------------------
# 4. 판정 (3일차 judge_cap과 같은 구조)
# --------------------------------------------------
def judge(area_ratio, rule):
    if rule["ok_when_greater"]:
        is_ok = area_ratio >= rule["area_ratio_threshold"]
    else:
        is_ok = area_ratio <= rule["area_ratio_threshold"]

    return ("OK", "") if is_ok else ("NG", "NG_CABLE_AREA")


# --------------------------------------------------
# 5. 가벼운 검사: 측정 + 판정만 (결과 이미지는 만들지 않음)
#    실시간 영상은 1초에 여러 번 검사하므로 빠른 버전이 필요합니다.
# --------------------------------------------------
def measure_and_judge(roi_image, rule):
    features, _, cleaned, largest = measure_features(roi_image, rule["method"])
    ratio = features["largest_area_ratio"]
    decision, reason = judge(ratio, rule)
    return {
        "decision": decision,
        "reason": reason,
        "ratio": ratio,
        "features": features,
        "cleaned": cleaned,
        "largest": largest,
    }


# --------------------------------------------------
# 6. 기준 이미지 2장으로 Rule 만들기 (p04와 같은 계산)
#    웹캠 화면에서 OK / NG 기준을 다시 잡을 때 사용합니다.
# --------------------------------------------------
def make_rule(ok_image, ng_image, rule_version, method="fixed"):
    ok_ratio = measure_features(ok_image, method)[0]["largest_area_ratio"]
    ng_ratio = measure_features(ng_image, method)[0]["largest_area_ratio"]

    if ok_ratio == ng_ratio:
        raise ValueError("OK와 NG 측정값이 같아서 구분할 수 없습니다. ROI나 조명을 확인하세요.")

    return {
        "rule_version": rule_version,
        "method": method,
        "fixed_threshold": cable_features.FIXED_THRESHOLD,
        "feature": "largest_area_ratio",
        "ok_reference_ratio": ok_ratio,
        "ng_reference_ratio": ng_ratio,
        "area_ratio_threshold": (ok_ratio + ng_ratio) / 2.0,
        "ok_when_greater": ok_ratio > ng_ratio,
    }


# --------------------------------------------------
# 7. 최종 검사 함수: 사진 검사 API가 호출하는 입구
# --------------------------------------------------
def inspect_image(image, rule, roi=None, source=""):
    roi_image, box = crop_roi(image, roi)

    measured = measure_and_judge(roi_image, rule)
    features = measured["features"]
    cleaned, largest = measured["cleaned"], measured["largest"]
    ratio, decision, reason = measured["ratio"], measured["decision"], measured["reason"]

    # 결과 화면용 이미지: 초록 Contour + 판정 글자
    annotated = roi_image.copy()
    if largest is not None:
        cv2.drawContours(annotated, [largest], -1, (0, 255, 0), 2)
    color = (0, 170, 0) if decision == "OK" else (0, 0, 230)
    cv2.putText(annotated, f"{decision} {ratio:.3f}", (6, 22),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return {
        "source": source,
        "decision": decision,
        "reason": reason,
        "area_ratio": round(ratio, 4),
        "area_ratio_threshold": round(rule["area_ratio_threshold"], 4),
        "valid_count": features["valid_count"],
        "roi_pixels": list(box) if box else None,
        "roi_size": [roi_image.shape[1], roi_image.shape[0]],
        "rule_version": rule["rule_version"],
        "method": rule["method"],
        "annotated_image": encode_jpg_base64(annotated),
        "binary_image": encode_jpg_base64(cleaned),
    }
