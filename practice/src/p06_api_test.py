"""
API 자동 테스트 (서버를 켜지 않고 확인)

FastAPI의 TestClient는 "가짜 브라우저"처럼 API를 직접 호출해 줍니다.
uvicorn을 실행하지 않아도 엔드포인트가 제대로 동작하는지 볼 수 있습니다.

실행 (프로젝트 최상위에서):
    python practice/src/p06_api_test.py
"""

import base64
from pathlib import Path

from fastapi.testclient import TestClient

from api_server import app


BASE_DIR = Path(__file__).resolve().parent.parent
client = TestClient(app)


# 1. 서버 상태 + Rule
health = client.get("/api/health").json()
print("health :", health)

# 2. 샘플 목록 → 테스트 이미지 전체 검사 (p05와 결과가 같아야 정상)
samples = client.get("/api/samples").json()
right = 0
for name in samples["test"]:
    result = client.post("/api/inspect/sample",
                         json={"folder": "test", "file_name": name}).json()
    right += result["correct"]
    mark = "O" if result["correct"] else "X"
    print(f"[{mark}] {name:16s} 판정={result['decision']} ratio={result['area_ratio']:.4f}")
print(f"정답 {right} / {len(samples['test'])}")

# 3. 원본 사진 업로드 + ROI 지정 (p01에서 잡은 ROI와 비슷한 위치를 비율로 전달)
for label in ["ok", "ng"]:
    raw = (BASE_DIR / "samples" / "raw" / f"{label}_raw.png").read_bytes()
    payload = {
        "image_base64": base64.b64encode(raw).decode("ascii"),
        "file_name": f"{label}_raw.png",
        "roi": {"x1": 0.40, "y1": 0.25, "x2": 0.73, "y2": 0.55},
    }
    response = client.post("/api/inspect/upload", json=payload)
    body = response.json()
    print(f"upload {label}: status={response.status_code} 판정={body.get('decision')} "
          f"ratio={body.get('area_ratio')} roi_px={body.get('roi_pixels')}")

# 4. 잘못된 요청은 에러로 막히는지
tiny = client.post("/api/inspect/upload", json={
    "image_base64": payload["image_base64"],
    "roi": {"x1": 0.5, "y1": 0.5, "x2": 0.501, "y2": 0.501},
})
print("너무 작은 ROI :", tiny.status_code, tiny.json()["detail"])

bad = client.post("/api/inspect/sample", json={"folder": "test", "file_name": "없는파일.jpg"})
print("없는 파일     :", bad.status_code, bad.json()["detail"])

print("기록 개수     :", len(client.get("/api/history").json()))
