from pathlib import Path
import shutil

import cv2


image_path = Path(
    "samples/day02/challenge.jpg"
)

temp_dir = Path(
    "roi_temp"
)

backup_path = (
    temp_dir / "challenge_original.jpg"
)

temp_dir.mkdir(
    parents=True,
    exist_ok=True,
)


# --------------------------------------------------
# 이미지 읽기
# --------------------------------------------------

image = cv2.imread(
    str(image_path)
)

if image is None:
    raise FileNotFoundError(
        f"이미지를 읽지 못했습니다: {image_path}"
    )


# --------------------------------------------------
# 원본 백업
# --------------------------------------------------

if not backup_path.exists():

    shutil.copy2(
        image_path,
        backup_path,
    )

    print(
        "원본 백업:",
        backup_path,
    )


# --------------------------------------------------
# 화면 크기 조절
# --------------------------------------------------

height, width = image.shape[:2]

max_width = 900
max_height = 700

scale = min(
    1.0,
    max_width / width,
    max_height / height,
)

display_width = int(
    width * scale
)

display_height = int(
    height * scale
)

preview = cv2.resize(
    image,
    (
        display_width,
        display_height,
    ),
)


# --------------------------------------------------
# ROI 선택 변수
# --------------------------------------------------

start_point = None
end_point = None

dragging = False
roi_selected = False


# --------------------------------------------------
# 마우스 이벤트
# --------------------------------------------------

def mouse_callback(
    event,
    x,
    y,
    flags,
    param,
):

    global start_point
    global end_point
    global dragging
    global roi_selected

    # 마우스 왼쪽 버튼 누름
    if event == cv2.EVENT_LBUTTONDOWN:

        start_point = (
            x,
            y,
        )

        end_point = (
            x,
            y,
        )

        dragging = True
        roi_selected = False


    # 마우스를 누른 상태로 이동
    elif (
        event == cv2.EVENT_MOUSEMOVE
        and dragging
    ):

        end_point = (
            x,
            y,
        )


    # 마우스 버튼 놓음
    elif event == cv2.EVENT_LBUTTONUP:

        end_point = (
            x,
            y,
        )

        dragging = False
        roi_selected = True

        print(
            "ROI 선택:",
            start_point,
            "→",
            end_point,
        )


# --------------------------------------------------
# Window
# --------------------------------------------------

window_name = (
    "ROI - Drag and press ENTER"
)

cv2.namedWindow(
    window_name,
    cv2.WINDOW_AUTOSIZE,
)

cv2.setMouseCallback(
    window_name,
    mouse_callback,
)


print()
print("ROI 선택 방법")
print("-----------------------------")
print("1. 병뚜껑 왼쪽 위에서")
print("   마우스 왼쪽 버튼을 누릅니다.")
print()
print("2. 버튼을 누른 상태로")
print("   오른쪽 아래까지 드래그합니다.")
print()
print("3. 마우스를 놓습니다.")
print()
print("4. 초록색 사각형을 확인합니다.")
print()
print("5. ENTER 또는 SPACE : 저장")
print("6. C : 다시 선택")
print("7. ESC : 취소")
print("-----------------------------")
print()


# --------------------------------------------------
# ROI 선택 화면
# --------------------------------------------------

while True:

    canvas = preview.copy()

    if (
        start_point is not None
        and end_point is not None
    ):

        cv2.rectangle(
            canvas,
            start_point,
            end_point,
            (0, 255, 0),
            2,
        )

    cv2.imshow(
        window_name,
        canvas,
    )

    key = (
        cv2.waitKey(20)
        & 0xFF
    )


    # ESC
    if key == 27:

        cv2.destroyAllWindows()

        print(
            "ROI 선택 취소"
        )

        raise SystemExit


    # C
    if key in (
        ord("c"),
        ord("C"),
    ):

        start_point = None
        end_point = None

        dragging = False
        roi_selected = False

        print(
            "ROI 다시 선택"
        )


    # ENTER 또는 SPACE
    if key in (
        13,
        10,
        32,
    ):

        if not roi_selected:

            print(
                "먼저 ROI를 드래그하세요."
            )

            continue

        break


cv2.destroyAllWindows()


# --------------------------------------------------
# 좌표 정리
# --------------------------------------------------

x1, y1 = start_point
x2, y2 = end_point

left = min(
    x1,
    x2,
)

right = max(
    x1,
    x2,
)

top = min(
    y1,
    y2,
)

bottom = max(
    y1,
    y2,
)


# --------------------------------------------------
# 화면 좌표 → 원본 좌표
# --------------------------------------------------

left = int(
    left / scale
)

right = int(
    right / scale
)

top = int(
    top / scale
)

bottom = int(
    bottom / scale
)


# --------------------------------------------------
# ROI Crop
# --------------------------------------------------

roi = image[
    top:bottom,
    left:right,
]

if roi.size == 0:

    raise ValueError(
        "ROI 영역이 올바르지 않습니다."
    )


# --------------------------------------------------
# ROI 저장
# --------------------------------------------------

cv2.imwrite(
    str(image_path),
    roi,
)


print()
print("ROI 저장 완료")
print("-----------------------------")
print("left   :", left)
print("top    :", top)
print("right  :", right)
print("bottom :", bottom)
print()
print(
    "저장:",
    image_path,
)