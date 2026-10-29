from pathlib import Path

from day05_logo_features import (
    prepare_reference,
    measure_target,
)


ROOT = Path(
    "samples/day05/mini_challenge"
)

REFERENCE_PATH = (
    ROOT
    / "reference/reference_label.jpg"
)

CALIBRATION_DIR = (
    ROOT
    / "calibration"
)

TEST_DIR = (
    ROOT
    / "test"
)


# --------------------------------------------------
# TODO 1
#
# Reference를 준비합니다.
#
# prepare_reference()를 사용합니다.
# --------------------------------------------------


# --------------------------------------------------
# TODO 2
#
# calibration/ok
# calibration/ng
#
# 이미지를 모두 읽어서 측정합니다.
#
# 확인할 값:
#
# template_score
# sift_good_matches
# homography_found
# homography_inliers
# inlier_ratio
# --------------------------------------------------


# --------------------------------------------------
# TODO 3
#
# OK와 NG 측정값을 비교합니다.
#
# 어떤 Feature가 구분에 도움이 되는지
# 최소 2개 확인합니다.
# --------------------------------------------------


# --------------------------------------------------
# TODO 4
#
# Calibration 결과를 보고
# Threshold를 결정합니다.
#
# 예:
#
# SIFT >= ?
# Inlier Ratio >= ?
#
# 숫자를 임의로 정하지 않습니다.
# --------------------------------------------------


# --------------------------------------------------
# TODO 5
#
# 결정한 Rule을 고정합니다.
#
# Test를 시작한 뒤에는
# Threshold를 수정하지 않습니다.
# --------------------------------------------------


# --------------------------------------------------
# TODO 6
#
# test/ok
# test/ng
#
# 이미지에 같은 Rule을 적용합니다.
# --------------------------------------------------


# --------------------------------------------------
# TODO 7
#
# Actual과 Predicted를 비교합니다.
#
# TP
# TN
# FP
# FN
#
# 을 확인합니다.
# --------------------------------------------------


print(
    "Day05 Mini Challenge를 완성하세요."
)