from pathlib import Path
import csv
import json

import cv2
import numpy as np

import cable_features
from cable_features import measure_features


# --------------------------------------------------
# 1. 경로 설정
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

TEST_DIR = BASE_DIR / "samples" / "test"
RULE_PATH = BASE_DIR / "configs" / "cable_rule.json"
OUTPUT_DIR = BASE_DIR / "outputs" / "p05_batch"
REPORT_PATH = BASE_DIR / "reports" / "p05_test_results.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. 저장된 Rule 불러오기 (p04에서 고정한 값 그대로 사용)
# --------------------------------------------------
if not RULE_PATH.exists():
    raise FileNotFoundError("p04를 먼저 실행하세요: configs/cable_rule.json")

rule = json.loads(RULE_PATH.read_text(encoding="utf-8"))

# Rule을 만들 때 쓴 고정 Threshold와 같은 값으로 측정해야 공정합니다.
cable_features.FIXED_THRESHOLD = rule["fixed_threshold"]


def judge(area_ratio):
    """Area Ratio를 기준값과 비교해 (판정, 이유)를 반환합니다."""
    if rule["ok_when_greater"]:
        is_ok = area_ratio >= rule["area_ratio_threshold"]
    else:
        is_ok = area_ratio <= rule["area_ratio_threshold"]

    return ("OK", "") if is_ok else ("NG", "NG_CABLE_AREA")


# --------------------------------------------------
# 3. 테스트 이미지 전체 검사
#    파일명 앞부분(ok_ / ng_)을 실제 정답으로 사용합니다.
# --------------------------------------------------
test_files = sorted(TEST_DIR.glob("*.jpg"))
if not test_files:
    raise FileNotFoundError("p02를 먼저 실행하세요: samples/test 이미지가 없습니다.")

rows = []
tiles = []

for path in test_files:
    image = cv2.imread(str(path))
    if image is None:
        print("읽기 실패:", path.name)
        continue

    actual = "OK" if path.name.startswith("ok_") else "NG"

    features, _, _, largest = measure_features(image, rule["method"])
    ratio = features["largest_area_ratio"]
    decision, reason = judge(ratio)
    correct = decision == actual

    rows.append({
        "file": path.name,
        "actual": actual,
        "decision": decision,
        "correct": correct,
        "area_ratio": round(ratio, 4),
        "reason": reason,
        "rule_version": rule["rule_version"],
    })

    # 결과 이미지: Contour(초록) + 판정 글자
    result = image.copy()
    if largest is not None:
        cv2.drawContours(result, [largest], -1, (0, 255, 0), 2)

    color = (0, 200, 0) if decision == "OK" else (0, 0, 255)
    cv2.putText(result, f"{decision} {ratio:.3f}", (4, 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    cv2.putText(result, path.stem, (4, result.shape[0] - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
    if not correct:
        cv2.rectangle(result, (0, 0), (result.shape[1] - 1, result.shape[0] - 1),
                      (0, 0, 255), 3)   # 틀린 결과는 빨간 테두리

    cv2.imwrite(str(OUTPUT_DIR / f"{path.stem}_result.jpg"), result)
    tiles.append(result)

    mark = "O" if correct else "X"
    print(f"[{mark}] {path.name:16s} 실제={actual} 판정={decision} "
          f"ratio={ratio:.4f} {reason}")


# --------------------------------------------------
# 4. 결과 저장 + 정확도
# --------------------------------------------------
with REPORT_PATH.open("w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

# 결과를 한 장으로 모아 보기 (5장씩 2줄: 위 NG, 아래 OK)
half = len(tiles) // 2
if half and len(tiles) == half * 2:
    sheet = np.vstack([np.hstack(tiles[:half]), np.hstack(tiles[half:])])
    cv2.imwrite(str(OUTPUT_DIR / "batch_sheet.png"), sheet)

correct_count = sum(r["correct"] for r in rows)
print()
print(f"Rule        : {rule['rule_version']} "
      f"(method={rule['method']}, threshold={rule['area_ratio_threshold']:.4f})")
print(f"정답        : {correct_count} / {len(rows)}")
print(f"Accuracy    : {correct_count / len(rows):.2%}")
print("CSV         :", REPORT_PATH)
