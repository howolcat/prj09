"""
케이블 체결 검사 FastAPI 서버

실행 (프로젝트 최상위 subject9_machinevision 에서):
    uvicorn api_server:app --app-dir practice/src --reload

브라우저:
    http://127.0.0.1:8000        검사 화면
    http://127.0.0.1:8000/docs   API 문서 (FastAPI가 자동으로 만들어 줌)
"""

from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cable_inspector import decode_base64_image, inspect_image, load_rule


# --------------------------------------------------
# 1. 경로 설정
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_PAGE = BASE_DIR / "web" / "cable_inspection.html"

# 화면에서 골라서 검사할 수 있는 샘플 폴더
SAMPLE_DIRS = {
    "reference": BASE_DIR / "samples" / "reference",
    "test": BASE_DIR / "samples" / "test",
}

HISTORY_SIZE = 20   # 최근 검사 기록 몇 개를 보관할지


# --------------------------------------------------
# 2. 서버 상태
#    rule    : 서버가 켜질 때 한 번 읽어 둔 Rule
#    history : 최근 검사 기록 (deque는 개수가 넘치면 오래된 것부터 자동 삭제)
# --------------------------------------------------
app = FastAPI(title="Cable Inspection API", version="1.0")

state = {
    "rule": load_rule(),
    "history": deque(maxlen=HISTORY_SIZE),
}


# --------------------------------------------------
# 3. 요청 형식 (Pydantic Model)
#    "이 API에는 이런 모양의 JSON을 보내야 한다"는 약속입니다.
#    형식이 틀리면 FastAPI가 알아서 422 에러를 돌려줍니다.
# --------------------------------------------------
class Roi(BaseModel):
    # 0~1 사이 비율 좌표 (ge=이상, le=이하)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)


class SampleRequest(BaseModel):
    folder: str = "test"            # reference 또는 test
    file_name: str                  # 예: ok_bright.jpg


class UploadRequest(BaseModel):
    image_base64: str               # 브라우저에서 읽은 이미지 (Base64 문자열)
    file_name: str = "upload"
    roi: Roi | None = None          # 없으면 이미지 전체를 검사


# --------------------------------------------------
# 4. 공통 처리: 검사 실행 + 기록 저장
# --------------------------------------------------
def run_inspection(image, roi, source, actual=None):
    roi_dict = None
    if roi is not None:
        roi_dict = roi.model_dump()
        # 드래그 방향과 상관없이 x1 < x2, y1 < y2 가 되도록 정리
        roi_dict = {
            "x1": min(roi.x1, roi.x2), "x2": max(roi.x1, roi.x2),
            "y1": min(roi.y1, roi.y2), "y2": max(roi.y1, roi.y2),
        }

    try:
        result = inspect_image(image, state["rule"], roi_dict, source)
    except ValueError as error:
        # ROI가 너무 작은 경우 등 → 400 Bad Request
        raise HTTPException(status_code=400, detail=str(error)) from error

    result["inspected_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 정답을 알고 있는 샘플이면 판정과 비교 (기록에 넣기 전에 추가해야 함)
    if actual is not None:
        result["actual"] = actual
        result["correct"] = actual == result["decision"]

    # 기록에는 무거운 이미지 문자열은 빼고 숫자만 저장
    summary = {k: v for k, v in result.items()
               if k not in ("annotated_image", "binary_image")}
    state["history"].appendleft(summary)

    return result


# --------------------------------------------------
# 5. API 엔드포인트
# --------------------------------------------------
@app.get("/")
def index():
    """검사 화면(HTML)을 돌려줍니다."""
    return FileResponse(WEB_PAGE)


@app.get("/api/health")
def health():
    """서버가 살아 있는지 확인하는 용도"""
    return {"status": "ok", "rule_version": state["rule"]["rule_version"]}


@app.get("/api/rule")
def get_rule():
    """현재 사용 중인 Rule(JSON) 확인"""
    return state["rule"]


@app.post("/api/reload-rule")
def reload_rule():
    """p04를 다시 실행해 Rule이 바뀌었을 때, 서버를 끄지 않고 다시 읽기"""
    try:
        state["rule"] = load_rule()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"message": "Rule을 다시 읽었습니다.", "rule": state["rule"]}


@app.get("/api/samples")
def list_samples():
    """화면의 샘플 선택 목록에 쓸 파일 이름들"""
    return {
        folder: sorted(p.name for p in path.glob("*.jpg"))
        for folder, path in SAMPLE_DIRS.items()
    }


@app.post("/api/inspect/sample")
def inspect_sample(request: SampleRequest):
    """서버에 저장된 샘플 이미지 1장 검사"""
    folder = SAMPLE_DIRS.get(request.folder)
    if folder is None:
        raise HTTPException(status_code=400, detail="folder는 reference 또는 test만 가능합니다.")

    # Path(...).name: "../../비밀파일" 같은 경로 조작을 막고 파일 이름만 사용
    path = folder / Path(request.file_name).name
    image = cv2.imread(str(path))
    if image is None:
        raise HTTPException(status_code=404, detail=f"샘플을 찾을 수 없습니다: {path.name}")

    # 파일명 앞부분(ok / ng)으로 정답을 알 수 있으면 같이 비교 (p05와 같은 방식)
    actual = None
    if path.name.startswith("ok"):
        actual = "OK"
    elif path.name.startswith("ng"):
        actual = "NG"

    return run_inspection(image, None, f"{request.folder}/{path.name}", actual)


@app.post("/api/inspect/upload")
def inspect_upload(request: UploadRequest):
    """브라우저에서 올린 이미지 검사 (ROI 선택 가능)"""
    try:
        image = decode_base64_image(request.image_base64)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return run_inspection(image, request.roi, f"upload/{request.file_name}")


@app.get("/api/history")
def history():
    """최근 검사 기록"""
    return list(state["history"])


@app.delete("/api/history")
def clear_history():
    state["history"].clear()
    return {"message": "기록을 지웠습니다."}
