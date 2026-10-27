"""
케이블 체결 검사 공통 함수 모음

p03, p04, p05에서 똑같은 측정 방법을 쓰기 위해 한곳에 모았습니다.
(5일차 day05_logo_features.py와 같은 역할)

    from cable_features import measure_features
"""

import cv2


# --------------------------------------------------
# 공통 설정값
# --------------------------------------------------
MIN_CONTOUR_AREA_RATIO = 0.001   # ROI 면적의 0.1% 미만 Contour는 Noise로 제외
FIXED_THRESHOLD = 80             # 고정 Threshold 기준 밝기 (p03 결과로 결정)

KERNEL = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))


def make_binary(gray, method):
    """
    Gray 이미지를 Binary로 바꿉니다.

    검사 대상(검은 케이블)이 배경보다 어두우므로
    두 방법 모두 THRESH_BINARY_INV를 사용합니다.
      → 어두운 픽셀 = 흰색(255) = 객체

    method
      "otsu"  : 밝기 분포를 보고 기준값을 자동 계산
      "fixed" : FIXED_THRESHOLD를 그대로 사용
    """
    if method == "otsu":
        threshold_value, binary = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
        )
    elif method == "fixed":
        threshold_value, binary = cv2.threshold(
            gray, FIXED_THRESHOLD, 255,
            cv2.THRESH_BINARY_INV,
        )
    else:
        raise ValueError(f"알 수 없는 method: {method}")

    return float(threshold_value), binary


def measure_features(image, method="fixed"):
    """
    ROI 이미지 한 장에서 Feature를 측정합니다. (3일차 20번 방식)

    처리 순서:
      Gray → Threshold(INV) → Opening → Closing
      → Contour → 작은 Contour 제외 → 가장 큰 Contour 측정

    반환값: (features 딕셔너리, binary, cleaned, largest_contour 또는 None)
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    threshold_value, binary = make_binary(gray, method)

    # Morphology: 작은 흰 점 제거 → 작은 검은 구멍 메우기
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, KERNEL, iterations=1)
    cleaned = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, KERNEL, iterations=1)

    contours, _ = cv2.findContours(
        cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )

    height, width = image.shape[:2]
    image_area = float(width * height)
    min_area = image_area * MIN_CONTOUR_AREA_RATIO

    valid = [c for c in contours if cv2.contourArea(c) >= min_area]

    features = {
        "method": method,
        "threshold": threshold_value,
        "valid_count": len(valid),
        "largest_area_ratio": 0.0,
        "touches_border": False,
        "gray_min": float(gray.min()),   # ROI에서 가장 어두운 밝기 (참고용)
    }

    if not valid:
        return features, binary, cleaned, None

    largest = max(valid, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)

    features["largest_area_ratio"] = cv2.contourArea(largest) / image_area
    features["touches_border"] = (
        x <= 0 or y <= 0 or x + w >= width or y + h >= height
    )

    return features, binary, cleaned, largest
