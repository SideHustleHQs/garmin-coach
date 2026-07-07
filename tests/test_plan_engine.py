import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from plan_engine import compute_paces


def test_compute_paces_from_goal_time():
    # sub-4 marathon: 14400s / 42.195km = 341 s/km marathonpace
    p = compute_paces(goal_time_s=14400, distance_km=42.195, current_easy_s=None)
    assert p["mp"] == 341
    assert p["easy"] == 376      # mp + 35
    assert p["long"] == 361      # mp + 20
    assert p["tempo"] == 316     # mp - 25
    assert p["interval"] == 286  # mp - 55


def test_compute_paces_without_goal_uses_current_easy():
    p = compute_paces(goal_time_s=None, distance_km=16.1, current_easy_s=360)
    # race-pace = current_easy - 20
    assert p["mp"] == 340
    assert p["easy"] == 360
