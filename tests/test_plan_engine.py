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


from plan_engine import phase_for_week

def test_phase_for_week_boundaries():
    total = 14
    assert phase_for_week(1, total) == "base"
    assert phase_for_week(4, total) == "base"    # <=30%
    assert phase_for_week(5, total) == "build"
    assert phase_for_week(10, total) == "build"  # <=70%
    assert phase_for_week(11, total) == "peak"
    assert phase_for_week(12, total) == "peak"   # <=85%
    assert phase_for_week(13, total) == "taper"
    assert phase_for_week(14, total) == "taper"


from plan_engine import long_run_progression

def test_long_run_progression_builds_cutbacks_and_tapers():
    lr = long_run_progression(total_weeks=14, start_km=14, peak_km=32)
    assert len(lr) == 14
    assert lr[0] == 14                    # week 1 = start
    assert lr[10] == 32 or lr[9] == 32    # piek ~3 wk voor eind (peak fase)
    assert lr[13] < lr[10]                # taper: laatste week korter dan piek
    assert lr[2] < lr[1] or lr[3] < lr[2] # cutback aanwezig in opbouw
    assert max(lr) == 32                  # piek = peak_km


from plan_engine import assemble_week

PREFS_ROWAN = {
    "run_days": ["mon", "thu", "sat"],
    "fixed_days": {"tue": "strength", "wed": "hyrox", "fri": "strength"},
}

def test_assemble_week_places_runs_and_respects_hyrox():
    days = assemble_week(
        run_days=PREFS_ROWAN["run_days"], fixed_days=PREFS_ROWAN["fixed_days"],
        long_km=20, easy_km=7, quality={"type": "tempo", "title": "Tempo 8 km"},
    )
    by = {d["weekday"]: d for d in days}
    assert len(days) == 7
    assert by["wed"]["day_type"] == "hyrox"
    assert by["tue"]["day_type"] == "strength"
    assert by["sat"]["run_type"] == "long"          # lange run in weekend-slot
    # thu volgt direct op hyrox(wed) → mag GEEN quality/long zijn
    assert by["thu"]["run_type"] == "easy"
    # quality op een run-dag die niet direct na hyrox valt (mon)
    assert by["mon"]["run_type"] == "quality"
    # dagen zonder run/fixed = rest
    assert by["sun"]["day_type"] == "rest"
