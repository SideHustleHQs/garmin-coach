import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from metrics import pace_at_hr, weekly_volume_km


def test_pace_at_hr_averages_runs_in_band():
    runs = [
        {"date": "2026-07-01", "distance_m": 10000, "duration_s": 3000, "avg_hr": 150},
        {"date": "2026-07-03", "distance_m": 8000, "duration_s": 2560, "avg_hr": 148},
        {"date": "2026-07-05", "distance_m": 5000, "duration_s": 1200, "avg_hr": 175},
    ]
    trend = pace_at_hr(runs, hr_min=145, hr_max=155)
    assert len(trend) == 2
    assert trend[0]["pace_s_per_km"] == 300.0
    assert trend[1]["pace_s_per_km"] == 320.0


def test_pace_at_hr_empty_when_no_runs_in_band():
    runs = [{"date": "2026-07-05", "distance_m": 5000, "duration_s": 1200, "avg_hr": 175}]
    assert pace_at_hr(runs, hr_min=145, hr_max=155) == []


def test_weekly_volume_sums_by_iso_week():
    runs = [
        {"date": "2026-06-29", "distance_m": 10000},
        {"date": "2026-07-01", "distance_m": 5000},
        {"date": "2026-07-06", "distance_m": 8000},
    ]
    weeks = weekly_volume_km(runs)
    assert weeks["2026-W27"] == 15.0
    assert weeks["2026-W28"] == 8.0
