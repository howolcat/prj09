# practice_label — 실시간 로고 부착 검사

> 4일차 특징점 매칭(SIFT + RANSAC + Homography)을 IP Webcam 실시간 영상에 적용하고,
> 판정 결과를 WebSocket으로 여러 화면에 전달하는 확장 프로젝트입니다.
> (진행 중 — 브랜치 `feat/label-live`)

- 검사 문제 정의: [reports/problem_definition.md](reports/problem_definition.md)
- 이전 프로젝트: [practice — 케이블 체결 검사 (1~3일차 복습)](../practice/)

## 진행 상황

- [x] 폴더 구조 + 검사 문제 정의
- [x] `l01_capture.py` — IP Webcam 화면에서 사진 저장
- [x] `l02_make_reference.py` — Reference 로고 자르기
- [ ] 촬영 (Reference / Calibration / Test)
- [ ] `label_inspector.py` — SIFT + Homography 측정 함수
- [ ] Calibration 측정 → Rule 고정 → Test 정확도
- [ ] 실시간 서버 + WebSocket
- [ ] (확장) 위치·각도 판정, 여러 화면 동시 모니터

## 실행 순서 (프로젝트 최상위 `subject9_machinevision`에서)

```bash
# 1. IP Webcam 화면에서 사진 저장 (r / 1 / 2 / 3 / 4 키, q 종료)
python practice_label/src/l01_capture.py --url http://휴대폰IP:8080/video

# 2. Reference 원본에서 로고 영역 자르기 (마우스 드래그 → Enter)
python practice_label/src/l02_make_reference.py
```

## 폴더 구조

```text
practice_label/
├── samples/
│   ├── reference/      reference_full_*.jpg (원본), reference.jpg (로고)
│   ├── calibration/    ok/, ng/   ← 기준값을 정할 사진
│   └── test/           ok/, ng/   ← Rule 고정 후 확인할 사진
├── src/                l01, l02 ...
├── web/                실시간 검사 화면
├── configs/            reference_roi.json, (예정) label_rule.json
├── reports/            problem_definition.md, 측정 CSV
├── outputs/            결과 이미지
└── docs/issues/        오류 해결 기록
```
