# practice — 충전기 케이블 체결 검사 (1~3일차 복습)

충전기에 케이블이 꽂혀 있으면 **OK**, 없으면 **NG**로 판정합니다.
1~3일차의 `ROI → 전처리·Threshold 비교 → Contour 측정 → Rule → Batch Test` 흐름을 다시 따라갑니다.

## 실행 순서 (프로젝트 최상위 `subject9_machinevision`에서)

```bash
python practice/src/p01_make_reference.py    # 원본 2장 → 기준 ROI (ok.jpg / ng.jpg)
python practice/src/p02_make_test_images.py  # 기준 ROI → 조건 변화 테스트 이미지 10장
python practice/src/p03_feature_compare.py   # Otsu vs 고정 Threshold 측정 비교
python practice/src/p04_make_rule.py         # 기준값 계산 → configs/cable_rule.json 저장
python practice/src/p05_batch_test.py        # 테스트 10장 판정 + 정확도
```

## API 서버 (p05까지 실행해서 `configs/cable_rule.json`이 있어야 함)

```bash
python practice/src/p06_api_test.py                          # 서버 없이 API 자동 테스트
uvicorn api_server:app --app-dir practice/src --reload       # 서버 실행 (끄기: Ctrl+C)
```

- 검사 화면: http://127.0.0.1:8000
- API 문서: http://127.0.0.1:8000/docs

| Method | 주소 | 역할 |
|---|---|---|
| GET | `/` | 검사 화면 (web/cable_inspection.html) |
| GET | `/api/health` | 서버 상태 + Rule 버전 |
| GET | `/api/rule` | 현재 Rule 보기 |
| POST | `/api/reload-rule` | Rule 파일 다시 읽기 |
| GET | `/api/samples` | reference / test 이미지 목록 |
| POST | `/api/inspect/sample` | 저장된 샘플 1장 검사 |
| POST | `/api/inspect/upload` | 업로드 이미지(Base64) + ROI 검사 |
| GET / DELETE | `/api/history` | 최근 검사 기록 보기 / 지우기 |

구조: `api_server.py`(요청·응답) → `cable_inspector.py`(검사 Service Core) → `cable_features.py`(측정)

## IP Webcam 실시간 검사 (깃 `src/fastapi_cap_app.py`와 같은 구조)

```bash
uvicorn live_server:app --app-dir practice/src --host 0.0.0.0 --port 8001
```

1. 휴대폰 IP Webcam 앱에서 「서버 시작」 → 화면에 나온 주소 확인 (PC와 같은 Wi-Fi)
2. http://127.0.0.1:8001 접속 → `http://휴대폰IP:8080/video` 입력 → 카메라 연결
3. 영상에서 충전기 입구를 드래그해서 ROI 지정 → 실시간 OK / NG
4. 판정이 이상하면: 케이블 꽂고 「OK 기준 저장」 → 빼고 「NG 기준 저장」 → 「웹캠 Rule 만들기」
   - 결과: `samples/live_reference/ok.jpg, ng.jpg`, `configs/cable_rule_live.json` (cable-live-v1.0)
   - 다음 실행 때는 웹캠 Rule이 있으면 자동으로 그것부터 사용

| Method | 주소 | 역할 |
|---|---|---|
| POST | `/api/camera` | IP Webcam 주소 연결 (사설 IP만 허용) |
| POST / DELETE | `/api/roi` | ROI 지정 / 초기화 |
| GET | `/api/status` | 실시간 판정·Ratio·Rule 상태 |
| GET | `/stream.mjpg` | 검사 결과가 그려진 실시간 영상 |
| POST | `/api/reference/{ok\|ng}` | 현재 ROI를 웹캠 기준 이미지로 저장 |
| POST | `/api/live-rule` | 웹캠 기준 2장으로 Rule 생성 + 적용 |
| POST | `/api/use-rule` | `photo` / `live` Rule 바꾸기 |

## 폴더 구조

```text
practice/
├── samples/
│   ├── raw/        ok_raw.png, ng_raw.png  (휴대폰 원본)
│   ├── reference/  ok.jpg, ng.jpg          (p01)
│   └── test/       ok_*.jpg, ng_*.jpg      (p02)
├── src/
│   ├── cable_features.py   공통 측정 함수
│   ├── p01 ~ p05           1~3일차 흐름
│   ├── cable_inspector.py  검사 Service Core (API용)
│   ├── api_server.py       FastAPI 서버 (사진 검사)
│   ├── live_server.py      FastAPI 서버 (IP Webcam 실시간 검사)
│   └── p06_api_test.py     API 자동 테스트
├── web/
│   ├── cable_inspection.html  사진 검사 화면
│   └── cable_live.html        실시간 검사 화면
├── configs/cable_rule.json (p04)
├── outputs/                결과 이미지
└── reports/                결과 CSV
```

## 결과 요약 (cable-v1.0)

| 측정 방법 | OK area ratio | NG area ratio | 판단 |
|---|---|---|---|
| Otsu (3일차 교재 방식) | 0.167 | 0.911 | 방향이 거꾸로 → 사용 안 함 |
| 고정 Threshold 80 | 0.129 | 0.000 | OK > NG → 채택 |

- 기준값: 0.0643 (두 값의 중간)
- 테스트 10장: 9 / 10 정답 (`ok_bright` 1장 실패)

## 배운 점

- Otsu는 어두운 물체가 없어도 **반드시 둘로 나누기 때문에**, NG 이미지에서 배경 전체를 객체로 잡았다.
- 고정 Threshold는 NG를 확실히 걸렀지만, 밝기가 +30 올라가자 케이블 일부가 80을 넘어 OK를 놓쳤다.
- 테스트 이미지는 같은 사진의 변형이므로, 실제 성능은 새로 촬영한 사진으로 다시 확인해야 한다.
