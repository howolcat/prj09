from pathlib import Path
import cv2


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

stream_url = "http://192.168.40.121:8080/video"

output_dir = Path("outputs/live_roi")
output_dir.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# ROI 선택 상태
# --------------------------------------------------

drawing = False

start_x = 0
start_y = 0

end_x = 0
end_y = 0

roi_selected = False


# --------------------------------------------------
# 마우스로 ROI 선택
# --------------------------------------------------

def mouse_callback(event, x, y, flags, param):

    global drawing
    global start_x, start_y
    global end_x, end_y
    global roi_selected

    # 마우스 왼쪽 버튼을 누르면 시작점 기록
    if event == cv2.EVENT_LBUTTONDOWN:

        drawing = True

        start_x = x
        start_y = y

        end_x = x
        end_y = y

        roi_selected = False


    # 마우스를 움직이는 동안 영역 표시
    elif event == cv2.EVENT_MOUSEMOVE and drawing:

        end_x = x
        end_y = y


    # 마우스 버튼을 놓으면 ROI 확정
    elif event == cv2.EVENT_LBUTTONUP:

        drawing = False

        end_x = x
        end_y = y

        roi_selected = True

        print(
            "ROI 선택:",
            start_x,
            start_y,
            end_x,
            end_y
        )


# --------------------------------------------------
# 스마트폰 영상 연결
# --------------------------------------------------

cap = cv2.VideoCapture(stream_url)

if not cap.isOpened():
    raise RuntimeError(
        "스마트폰 영상을 열 수 없습니다."
    )


window_name = "Phone Camera"

cv2.namedWindow(window_name)

cv2.setMouseCallback(
    window_name,
    mouse_callback
)


print()
print("===================================")
print("스마트폰 실시간 ROI 실습")
print("===================================")
print("마우스 드래그 : ROI 선택")
print("r            : ROI 다시 선택")
print("1            : 뚜껑 있음 저장")
print("2            : 뚜껑 없음 저장")
print("q / ESC      : 종료")
print("Ctrl + C     : 터미널에서 강제 종료")
print("===================================")
print()


try:

    while True:

        ret, frame = cap.read()

        if not ret:
            print("Frame을 읽을 수 없습니다.")
            break


        preview = frame.copy()


        # ------------------------------------------
        # ROI 선택 중
        # ------------------------------------------

        if drawing:

            cv2.rectangle(
                preview,
                (start_x, start_y),
                (end_x, end_y),
                (0, 255, 255),
                2
            )


        # ------------------------------------------
        # ROI가 선택된 경우
        # ------------------------------------------

        if roi_selected:

            x1 = min(start_x, end_x)
            y1 = min(start_y, end_y)

            x2 = max(start_x, end_x)
            y2 = max(start_y, end_y)


            # 전체 화면에 ROI 표시
            cv2.rectangle(
                preview,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                3
            )


            cv2.putText(
                preview,
                "CAP ROI",
                (x1, max(30, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )


            # ROI 자르기
            roi = frame[y1:y2, x1:x2]


            if roi.size > 0:

                cv2.imshow(
                    "Cap ROI",
                    roi
                )


        # 전체 실시간 영상
        cv2.imshow(
            window_name,
            preview
        )


        # ------------------------------------------
        # 키 입력
        # ------------------------------------------

        key = cv2.waitKey(1) & 0xFF


        # q 또는 ESC → 종료
        if key == ord("q") or key == 27:
            print("프로그램을 종료합니다.")
            break


        # r → ROI 초기화
        elif key == ord("r"):

            roi_selected = False

            print("ROI를 다시 선택하세요.")

            try:
                cv2.destroyWindow("Cap ROI")
            except cv2.error:
                pass


        # 1 → 병뚜껑 있음 저장
        elif key == ord("1") and roi_selected:

            output_path = (
                output_dir / "cap_on.jpg"
            )

            cv2.imwrite(
                str(output_path),
                roi
            )

            print(
                "병뚜껑 있음 저장:",
                output_path
            )


        # 2 → 병뚜껑 없음 저장
        elif key == ord("2") and roi_selected:

            output_path = (
                output_dir / "cap_off.jpg"
            )

            cv2.imwrite(
                str(output_path),
                roi
            )

            print(
                "병뚜껑 없음 저장:",
                output_path
            )


        # 창의 X 버튼으로 닫았는지도 확인
        try:

            if (
                cv2.getWindowProperty(
                    window_name,
                    cv2.WND_PROP_VISIBLE
                )
                < 1
            ):
                print("창이 닫혀 프로그램을 종료합니다.")
                break

        except cv2.error:
            break


# Ctrl + C 처리
except KeyboardInterrupt:

    print()
    print("Ctrl + C가 입력되었습니다.")
    print("프로그램을 종료합니다.")


# 어떤 상황에서도 자원 정리
finally:

    cap.release()

    cv2.destroyAllWindows()

    print("카메라 연결을 종료했습니다.")