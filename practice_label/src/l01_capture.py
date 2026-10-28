"""
l01_capture.py — IP Webcam 화면에서 검사용 사진을 바로 저장합니다.

왜 카메라 앱이 아니라 IP Webcam으로 찍을까요?
    나중에 실시간 검사도 IP Webcam 영상으로 하기 때문입니다.
    기준 사진과 실시간 영상의 카메라·해상도·거리가 같아야
    측정값(Inlier 수, Inlier Ratio)을 그대로 비교할 수 있습니다.

실행 (프로젝트 최상위 subject9_machinevision 에서):
    python practice_label/src/l01_capture.py --url http://192.168.0.25:8080/video

키 안내:
    r : Reference 원본 저장 (정면, 정상 위치 1장)
    1 : Calibration OK 저장   (기준값을 정할 정상 사진)
    2 : Calibration NG 저장   (기준값을 정할 불량 사진)
    3 : Test OK 저장          (Rule 고정 후 확인할 정상 사진)
    4 : Test NG 저장          (Rule 고정 후 확인할 불량 사진)
    q / ESC : 종료
"""

import argparse
from pathlib import Path

import cv2


# --------------------------------------------------
# 1. 경로와 기본 설정
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent      # practice_label/
SAMPLE_DIR = BASE_DIR / "samples"

DEFAULT_URL = "http://192.168.0.25:8080/video"        # 내 휴대폰 주소로 바꾸거나 --url 사용
EXPECTED_SIZE = (640, 480)                             # IP Webcam 해상도 통일 기준 (가로, 세로)
MAX_READ_FAIL = 30                                     # 연속으로 이만큼 못 읽으면 종료

# 키 → (저장 폴더, 파일 이름 앞부분, 이름, 화면용 짧은 이름)
SAVE_KEYS = {
    ord("r"): (SAMPLE_DIR / "reference", "reference_full", "Reference", "ref"),
    ord("1"): (SAMPLE_DIR / "calibration" / "ok", "ok", "Calibration OK", "calOK"),
    ord("2"): (SAMPLE_DIR / "calibration" / "ng", "ng", "Calibration NG", "calNG"),
    ord("3"): (SAMPLE_DIR / "test" / "ok", "ok", "Test OK", "testOK"),
    ord("4"): (SAMPLE_DIR / "test" / "ng", "ng", "Test NG", "testNG"),
}


# --------------------------------------------------
# 2. 저장할 파일 이름 정하기
#    ok_001.jpg, ok_002.jpg ... 처럼 빈 번호를 자동으로 찾습니다.
#    (이미 있는 파일을 덮어쓰지 않기 위해서)
# --------------------------------------------------
def next_save_path(folder, prefix):
    folder.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        path = folder / f"{prefix}_{number:03d}.jpg"
        if not path.exists():
            return path
        number += 1


def count_images(folder):
    return len(list(folder.glob("*.jpg"))) if folder.exists() else 0


# --------------------------------------------------
# 3. 화면 안내 글자 그리기
#    저장되는 사진에는 글자가 들어가지 않도록 '복사본'에만 그립니다.
# --------------------------------------------------
def draw_overlay(frame, message):
    view = frame.copy()
    height, width = view.shape[:2]

    lines = [
        f"size {width}x{height}",
        "r:Ref  1:CalOK  2:CalNG  3:TestOK  4:TestNG  q:quit",
    ]
    # 폴더별 저장 개수 표시 (예: ref=1  calOK=3  calNG=2 ...)
    counts = "  ".join(
        f"{short}={count_images(folder)}"
        for folder, _, _, short in SAVE_KEYS.values()
    )
    lines.append(counts)

    for i, text in enumerate(lines):
        y = 22 + i * 22
        cv2.putText(view, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
        cv2.putText(view, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # 해상도가 기준과 다르면 빨간 경고
    if (width, height) != EXPECTED_SIZE:
        warn = f"WARNING: expected {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]}"
        cv2.putText(view, warn, (8, height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

    if message:
        cv2.putText(view, message, (8, height - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

    return view


# --------------------------------------------------
# 4. 메인: 영상 읽기 → 화면 표시 → 키 입력으로 저장
# --------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="IP Webcam 검사 사진 캡처")
    parser.add_argument("--url", default=DEFAULT_URL, help="IP Webcam 영상 주소 (.../video)")
    args = parser.parse_args()

    cap = cv2.VideoCapture(args.url)
    if not cap.isOpened():
        raise RuntimeError(f"영상을 열 수 없습니다: {args.url}  (주소·Wi-Fi·IP Webcam 서버 확인)")

    window = "practice_label capture"
    cv2.namedWindow(window)

    print("=" * 50)
    print("키 안내:" + __doc__.split("키 안내:")[1].rstrip())   # 위 설명문의 키 안내 부분 출력
    print("=" * 50)

    message = ""
    read_fail = 0
    size_checked = False

    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                read_fail += 1
                if read_fail >= MAX_READ_FAIL:
                    print("프레임을 계속 읽지 못해 종료합니다.")
                    break
                continue
            read_fail = 0

            # 처음 한 번만 해상도 확인 메시지 출력
            if not size_checked:
                height, width = frame.shape[:2]
                print(f"영상 크기: {width}x{height}", end="  ")
                print("(OK)" if (width, height) == EXPECTED_SIZE
                      else f"→ IP Webcam 설정에서 {EXPECTED_SIZE[0]}x{EXPECTED_SIZE[1]}로 맞추세요")
                size_checked = True

            cv2.imshow(window, draw_overlay(frame, message))
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), 27):          # 27 = ESC
                break

            if key in SAVE_KEYS:
                folder, prefix, name, _ = SAVE_KEYS[key]
                path = next_save_path(folder, prefix)
                cv2.imwrite(str(path), frame)   # 글자 없는 원본 Frame 저장
                message = f"saved: {name} -> {path.name}"
                print(f"[저장] {name:15s} {path.relative_to(BASE_DIR)}")

            # 창의 X 버튼으로 닫았을 때도 종료
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    print("종료했습니다. 저장 개수:")
    for folder, _, name, _ in SAVE_KEYS.values():
        print(f"  {name:15s} {count_images(folder)}장")


if __name__ == "__main__":
    main()
