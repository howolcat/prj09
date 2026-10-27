"""
스마트폰 IP Webcam → OpenCV 케이블 검사 → FastAPI 실시간 웹 화면

깃의 src/fastapi_cap_app.py 구조를 그대로 따라갑니다.
    LiveState(상태 보관) + 카메라 스레드 + MJPEG 스트림 + 상태 API

실행 (프로젝트 최상위 subject9_machinevision 에서):
    uvicorn live_server:app --app-dir practice/src --host 0.0.0.0 --port 8001

브라우저: http://127.0.0.1:8001
"""

from contextlib import asynccontextmanager
import ipaddress
import json
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from cable_inspector import load_rule, make_rule, measure_and_judge, MIN_ROI_PIXELS


# --------------------------------------------------
# ① 경로 설정
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
HTML_FILE = BASE_DIR / "web" / "cable_live.html"

# Rule 파일 2종류
#   photo : p04에서 휴대폰 사진으로 만든 Rule
#   live  : 웹캠 화면에서 OK / NG 기준을 다시 찍어 만든 Rule
RULE_FILES = {
    "photo": BASE_DIR / "configs" / "cable_rule.json",
    "live": BASE_DIR / "configs" / "cable_rule_live.json",
}
LIVE_REFERENCE_DIR = BASE_DIR / "samples" / "live_reference"


# --------------------------------------------------
# ② 카메라 연결 전 보여 줄 대기 화면
# --------------------------------------------------
def placeholder_jpg():
    frame = np.full((480, 640, 3), (38, 43, 50), dtype=np.uint8)
    cv2.putText(frame, "IP WEBCAM - WAITING", (65, 227),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (230, 230, 230), 2)
    return cv2.imencode(".jpg", frame)[1].tobytes()


WAITING_JPG = placeholder_jpg()


# --------------------------------------------------
# ③ 실시간 검사 상태를 한곳에 모아 두는 클래스
#    카메라 스레드(쓰기)와 API 요청(읽기)이 동시에 접근하므로
#    lock으로 "한 번에 한 쪽만" 만지게 합니다.
# --------------------------------------------------
class LiveState:

    def __init__(self):
        self.lock = threading.Lock()
        self.url = None
        self.roi = None                  # (x1, y1, x2, y2) 0~1 비율
        self.rule = None
        self.rule_name = "photo"
        self.rule_error = "Rule 읽기 전"
        self.camera_status = "NOT_CONNECTED"
        self.message = "스마트폰 IP Webcam 주소를 연결하세요."
        self.decision = "WAIT"
        self.reason = ""
        self.ratio = None
        self.frame_size = None
        self.latest_jpg = WAITING_JPG
        self.latest_roi_image = None     # 기준 저장 버튼용 최신 ROI 이미지
        self.last_frame_time = 0.0
        self.stop_event = threading.Event()
        self.thread = None

    # ---------- Rule 읽기 / 바꾸기 ----------
    def use_rule(self, name):
        try:
            rule = load_rule(RULE_FILES[name])
        except FileNotFoundError as error:
            with self.lock:
                self.rule_error = str(error)
            return {"ok": False, "error": str(error)}

        with self.lock:
            self.rule = rule
            self.rule_name = name
            self.rule_error = ""
            self.decision = "WAIT"
        return {"ok": True, "rule_name": name, "rule": rule}

    # ---------- 서버 시작 / 종료 ----------
    def start(self):
        self.stop_event.clear()
        # 웹캠용 Rule이 이미 있으면 그것부터, 없으면 사진 Rule 사용
        if not self.use_rule("live")["ok"]:
            self.use_rule("photo")
        self.thread = threading.Thread(target=self.camera_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=3)

    # ---------- 카메라 주소 / ROI 저장 ----------
    def set_camera(self, url):
        with self.lock:
            self.url = url
            self.roi = None              # 다른 카메라에 이전 ROI를 쓰지 않음
            self.camera_status = "CONNECTING"
            self.message = "카메라 연결 중입니다."
            self.decision = "WAIT"
            self.ratio = None
            self.latest_jpg = WAITING_JPG
            self.latest_roi_image = None
            self.last_frame_time = 0.0

    def set_roi(self, roi):
        with self.lock:
            self.roi = roi
            self.decision = "WAIT"
            self.ratio = None
            self.reason = ""
            self.latest_roi_image = None

    # ---------- 현재 상태 (브라우저가 0.4초마다 물어봄) ----------
    def get_status(self):
        with self.lock:
            elapsed = (time.monotonic() - self.last_frame_time
                       if self.last_frame_time else None)
            camera_status = self.camera_status
            if camera_status == "ONLINE" and elapsed is not None and elapsed > 5:
                camera_status = "DISCONNECTED"   # 5초 넘게 새 프레임이 없으면 끊긴 것
            rule = self.rule
            return {
                "camera_status": camera_status,
                "message": self.message,
                "decision": self.decision if camera_status == "ONLINE" else "WAIT",
                "reason": self.reason,
                "ratio": self.ratio,
                "roi": self.roi,
                "frame_size": self.frame_size,
                "rule_ready": rule is not None,
                "rule_error": self.rule_error,
                "rule_name": self.rule_name,
                "rule_version": rule["rule_version"] if rule else None,
                "threshold": rule["area_ratio_threshold"] if rule else None,
                "ok_ratio": rule["ok_reference_ratio"] if rule else None,
                "ng_ratio": rule["ng_reference_ratio"] if rule else None,
                "live_reference": {
                    label: (LIVE_REFERENCE_DIR / f"{label}.jpg").exists()
                    for label in ("ok", "ng")
                },
                "live_rule_exists": RULE_FILES["live"].exists(),
            }

    # ---------- 카메라 스레드: 읽기 → ROI 검사 → JPEG 저장 반복 ----------
    def camera_loop(self):
        while not self.stop_event.is_set():
            with self.lock:
                url = self.url
            if not url:
                self.stop_event.wait(0.1)
                continue

            cap = cv2.VideoCapture(url)
            if not cap.isOpened():
                cap.release()
                with self.lock:
                    if self.url == url:
                        self.camera_status = "DISCONNECTED"
                        self.message = "IP Webcam 연결 실패: URL과 Wi-Fi를 확인하세요."
                self.stop_event.wait(1.0)
                continue

            try:
                while not self.stop_event.is_set():
                    with self.lock:
                        if self.url != url:
                            break                # 웹에서 카메라를 바꿨으면 다시 연결
                        roi_coords = self.roi
                        rule = self.rule

                    ok, frame = cap.read()
                    if not ok or frame is None:
                        with self.lock:
                            if self.url == url:
                                self.camera_status = "DISCONNECTED"
                                self.message = "프레임 수신 중단: 재연결을 시도합니다."
                                self.decision = "WAIT"
                                self.latest_jpg = WAITING_JPG
                        break

                    h, w = frame.shape[:2]
                    image = frame.copy()
                    decision, reason, ratio = "WAIT", "", None
                    roi_image = None

                    if roi_coords is not None:
                        nx1, ny1, nx2, ny2 = roi_coords
                        x1, x2 = max(0, round(nx1 * w)), min(w, round(nx2 * w))
                        y1, y2 = max(0, round(ny1 * h)), min(h, round(ny2 * h))

                        if x2 - x1 >= MIN_ROI_PIXELS and y2 - y1 >= MIN_ROI_PIXELS:
                            roi_image = frame[y1:y2, x1:x2].copy()

                            if rule is not None:
                                try:
                                    result = measure_and_judge(roi_image, rule)
                                    decision = result["decision"]
                                    reason = result["reason"]
                                    ratio = result["ratio"]
                                    # 찾은 케이블 Contour를 전체 화면 위치로 옮겨서 그리기
                                    if result["largest"] is not None:
                                        cv2.drawContours(image, [result["largest"]], -1,
                                                         (0, 255, 0), 2, offset=(x1, y1))
                                except cv2.error:
                                    decision, reason = "CHECK", "ROI_PROCESS_FAILED"

                            color = ((0, 190, 0) if decision == "OK"
                                     else (0, 0, 225) if decision == "NG"
                                     else (0, 200, 255))
                            cv2.rectangle(image, (x1, y1), (x2, y2), color, 3)
                    else:
                        cv2.putText(image, "SELECT ROI ON WEB PAGE", (15, 40),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 230, 255), 2)

                    line = f"{decision}  Area Ratio: {ratio:.3f}" if ratio is not None else decision
                    cv2.putText(image, line, (12, h - 18),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 245, 255), 2)

                    success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 77])
                    if success:
                        with self.lock:
                            # 방금 웹에서 ROI / Rule을 바꿨다면 이 프레임 결과는 버림
                            if self.url == url and self.roi == roi_coords and self.rule is rule:
                                self.latest_jpg = encoded.tobytes()
                                self.latest_roi_image = roi_image
                                self.camera_status = "ONLINE"
                                self.message = "영상 수신 중"
                                self.decision = decision
                                self.reason = reason
                                self.ratio = ratio
                                self.frame_size = [w, h]
                                self.last_frame_time = time.monotonic()
            finally:
                cap.release()
            self.stop_event.wait(0.1)


# --------------------------------------------------
# ④ 서버가 켜질 때 카메라 스레드 시작, 꺼질 때 정리 (Lifespan)
# --------------------------------------------------
state = LiveState()


@asynccontextmanager
async def lifespan(_: FastAPI):
    state.start()
    yield
    state.stop()


app = FastAPI(title="practice 케이블 실시간 검사", lifespan=lifespan)


# --------------------------------------------------
# ⑤ 요청 형식 (Pydantic)
# --------------------------------------------------
class CameraRequest(BaseModel):
    url: str


class RoiRequest(BaseModel):
    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)
    x2: float = Field(ge=0.0, le=1.0)
    y2: float = Field(ge=0.0, le=1.0)


class UseRuleRequest(BaseModel):
    name: str                         # "photo" 또는 "live"


# --------------------------------------------------
# ⑥ 화면 + 카메라 + ROI
# --------------------------------------------------
@app.get("/")
def index():
    return FileResponse(HTML_FILE, media_type="text/html")


@app.post("/api/camera")
def connect_camera(body: CameraRequest):
    url = body.url.strip()
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise HTTPException(400, "http://IP:PORT/video 형식으로 입력하세요.")
    try:
        # 같은 Wi-Fi 안의 주소(192.168.x.x 등)만 허용 → 외부 주소 접속 방지
        address = ipaddress.ip_address(parts.hostname)
        if not (address.is_private or address.is_loopback):
            raise ValueError
        _ = parts.port                # 숫자가 아닌 포트면 ValueError
    except ValueError:
        raise HTTPException(400, "스마트폰의 사설 IP 주소(예: 192.168.x.x)를 사용하세요.")

    state.set_camera(url)
    return {"ok": True, "message": "연결을 시도합니다."}


@app.post("/api/roi")
def set_roi(body: RoiRequest):
    if body.x2 - body.x1 < 0.03 or body.y2 - body.y1 < 0.03:
        raise HTTPException(400, "ROI가 너무 작습니다. 더 넓게 드래그하세요.")
    state.set_roi((body.x1, body.y1, body.x2, body.y2))
    return {"ok": True}


@app.delete("/api/roi")
def reset_roi():
    state.set_roi(None)
    return {"ok": True}


@app.get("/api/status")
def get_status():
    return state.get_status()


# --------------------------------------------------
# ⑦ 웹캠 기준 다시 잡기
#    사진으로 만든 Rule은 웹캠 화면(거리·조명·해상도)과 맞지 않을 수 있습니다.
#    그래서 웹캠 화면에서 OK 1장, NG 1장을 저장해 Rule을 새로 만듭니다.
#    (p01 기준 이미지 → p04 Rule 만들기를 웹에서 하는 것)
# --------------------------------------------------
@app.post("/api/reference/{label}")
def save_reference(label: str):
    if label not in ("ok", "ng"):
        raise HTTPException(400, "label은 ok 또는 ng만 가능합니다.")

    with state.lock:
        roi_image = state.latest_roi_image
    if roi_image is None:
        raise HTTPException(400, "카메라 연결과 ROI 선택을 먼저 해 주세요.")

    LIVE_REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = LIVE_REFERENCE_DIR / f"{label}.jpg"
    cv2.imwrite(str(path), roi_image)
    return {"ok": True, "saved": f"samples/live_reference/{path.name}",
            "size": [roi_image.shape[1], roi_image.shape[0]]}


@app.post("/api/live-rule")
def create_live_rule():
    ok_image = cv2.imread(str(LIVE_REFERENCE_DIR / "ok.jpg"))
    ng_image = cv2.imread(str(LIVE_REFERENCE_DIR / "ng.jpg"))
    if ok_image is None or ng_image is None:
        raise HTTPException(400, "OK 기준과 NG 기준을 둘 다 먼저 저장하세요.")

    try:
        rule = make_rule(ok_image, ng_image, "cable-live-v1.0")
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

    RULE_FILES["live"].write_text(json.dumps(rule, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
    state.use_rule("live")
    return {"ok": True, "rule": rule}


@app.post("/api/use-rule")
def use_rule(body: UseRuleRequest):
    if body.name not in RULE_FILES:
        raise HTTPException(400, "name은 photo 또는 live만 가능합니다.")
    result = state.use_rule(body.name)
    if not result["ok"]:
        raise HTTPException(404, result["error"])
    return result


# --------------------------------------------------
# ⑧ MJPEG 실시간 영상: JPEG를 계속 이어서 보내는 방식
# --------------------------------------------------
@app.get("/stream.mjpg")
def stream_video():
    def frames():
        while True:
            with state.lock:
                image_bytes = state.latest_jpg
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n"
                   b"Cache-Control: no-cache\r\n\r\n"
                   + image_bytes + b"\r\n")
            time.sleep(0.10)              # 최대 약 10장/초

    return StreamingResponse(
        frames(), media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store"},
    )
