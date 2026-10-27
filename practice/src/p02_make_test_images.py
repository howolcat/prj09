from pathlib import Path

import cv2
import numpy as np


# --------------------------------------------------
# 1. 경로 설정
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

REFERENCE_DIR = BASE_DIR / "samples" / "reference"
TEST_DIR = BASE_DIR / "samples" / "test"
TEST_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. 왜 테스트 이미지를 "만드나요?"
#
#    실제 사진은 OK 1장, NG 1장뿐입니다.
#    기준(Rule)을 만든 사진으로 다시 채점하면 성능 검증이 아닙니다. (3일차 19절)
#
#    그래서 2일차(dark/noise/blur 생성)와 4일차(shift/rotate 생성)처럼
#    기준 이미지에 촬영 조건 변화를 하나씩 줘서 테스트 이미지를 만듭니다.
#
#    ⚠ 같은 사진에서 만든 변형이므로 "새로 촬영한 사진"만큼 믿을 수는 없습니다.
#      → 이 결과는 "조건 변화에 얼마나 버티는가"를 보는 스트레스 테스트입니다.
# --------------------------------------------------
rng = np.random.default_rng(42)   # 난수 고정 → 실행할 때마다 같은 Noise


def make_variants(image):
    """기준 ROI 한 장으로 조건이 하나씩 다른 이미지 5장을 만듭니다."""
    height, width = image.shape[:2]
    variants = {}

    # ① 밝게: 조명이 강해진 경우 (beta +30)
    variants["bright"] = cv2.convertScaleAbs(image, alpha=1.0, beta=30)

    # ② 어둡게: 조명이 약해진 경우 (픽셀값 70%)
    variants["dark"] = cv2.convertScaleAbs(image, alpha=0.7, beta=0)

    # ③ 위치 이동: 제품이 오른쪽 8px, 아래 6px 밀린 경우
    move = np.float32([[1, 0, 8], [0, 1, 6]])
    variants["shift"] = cv2.warpAffine(
        image, move, (width, height), borderMode=cv2.BORDER_REPLICATE,
    )

    # ④ Noise: 카메라 잡음 (Gaussian Noise, 표준편차 12)
    noise = rng.normal(0, 12, image.shape)
    variants["noise"] = np.clip(
        image.astype(np.float32) + noise, 0, 255,
    ).astype(np.uint8)

    # ⑤ 흐림: 초점이 살짝 안 맞은 경우 (Gaussian Blur 7×7)
    variants["blur"] = cv2.GaussianBlur(image, (7, 7), 0)

    return variants


# --------------------------------------------------
# 3. ok / ng 기준 이미지마다 변형 5장씩 저장
#    파일명 앞부분(ok_ / ng_)이 정답 라벨이 됩니다.
# --------------------------------------------------
for label in ["ok", "ng"]:

    reference_path = REFERENCE_DIR / f"{label}.jpg"
    image = cv2.imread(str(reference_path))

    if image is None:
        raise FileNotFoundError(
            f"기준 이미지가 없습니다. p01을 먼저 실행하세요: {reference_path}"
        )

    for name, variant in make_variants(image).items():
        output_path = TEST_DIR / f"{label}_{name}.jpg"
        cv2.imwrite(str(output_path), variant)
        print("저장:", output_path.name)

print("테스트 이미지 생성 완료")
