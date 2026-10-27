from pathlib import Path

import cv2


image_path = Path(
    "samples/day02/challenge.jpg"
)

output_dir = Path(
    "outputs/day02/challenge"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True,
)


image = cv2.imread(
    str(image_path)
)

if image is None:
    raise FileNotFoundError(
        f"이미지를 읽지 못했습니다: {image_path}"
    )


# --------------------------------------------------
# TODO
#
# 1. 문제: 병뚜껑과 배경이 모두 밝은 회색 계열이라
#    두 영역의 밝기 차이가 작다.
# 2. 선택: CLAHE로 지역 대비를 개선한다.
# 3. Parameter: clipLimit / tileGridSize
# 4. 결과를 result에 저장한다.
# --------------------------------------------------


# CLAHE는 1채널 이미지에 적용하므로 Gray로 변환
gray = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2GRAY,
)

# clipLimit → 1.0 / 2.0 / 3.0으로 바꿔가며 비교
clahe = cv2.createCLAHE(
    clipLimit=2.0,
    tileGridSize=(8, 8),
)

result = clahe.apply(
    gray
)



# --------------------------------------------------
# 전처리 결과 저장
# --------------------------------------------------

result_path = (
    output_dir
    / "challenge_result.jpg"
)

cv2.imwrite(
    str(result_path),
    result,
)


# --------------------------------------------------
# Gray 변환
# --------------------------------------------------

def to_gray(source):

    if len(source.shape) == 2:
        return source

    return cv2.cvtColor(
        source,
        cv2.COLOR_BGR2GRAY,
    )


original_gray = to_gray(
    image
)

result_gray = to_gray(
    result
)


# --------------------------------------------------
# 전처리 전 Otsu
#
# 이번 Challenge에서는
# 밝은 병뚜껑을 흰색 객체로 확인합니다.
# --------------------------------------------------

_, original_otsu = cv2.threshold(
    original_gray,
    0,
    255,
    cv2.THRESH_BINARY
    + cv2.THRESH_OTSU,
)


# --------------------------------------------------
# 전처리 후 Otsu
# --------------------------------------------------

_, result_otsu = cv2.threshold(
    result_gray,
    0,
    255,
    cv2.THRESH_BINARY
    + cv2.THRESH_OTSU,
)


cv2.imwrite(
    str(
        output_dir
        / "challenge_original_otsu.jpg"
    ),
    original_otsu,
)

cv2.imwrite(
    str(
        output_dir
        / "challenge_result_otsu.jpg"
    ),
    result_otsu,
)


print("입력 :", image_path)
print("결과 :", result_path)
print("Challenge 완료")