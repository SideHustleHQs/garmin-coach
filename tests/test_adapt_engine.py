import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from adapt_engine import adjust_day
from adapt_engine import absorb_missed

PACES = {"mp": 341, "easy": 376, "long": 361, "tempo": 316, "interval": 286}

def _wo(run_type, target=None, km=None):
    return {"run_type": run_type, "title": "x", "target_pace_s": target, "distance_km": km,
            "segments": [{"label": "werk", "target_pace_s": target}] if target else None}

def test_low_readiness_downgrades_quality_to_easy():
    adj = adjust_day(_wo("quality", 316), {"readiness": 34, "acwr": 1.0}, PACES)
    assert adj and adj["adjusted_run_type"] == "easy"
    assert adj["adjusted_target_pace_s"] == PACES["easy"]
    assert "readiness" in adj["adjustment_reason"].lower() or "rustig" in adj["adjustment_reason"].lower()

def test_high_acwr_downgrades_long_to_easy():
    adj = adjust_day(_wo("long", 361, 20), {"readiness": 70, "acwr": 1.6}, PACES)
    assert adj and adj["adjusted_run_type"] == "easy"

def test_low_readiness_easy_becomes_rest():
    adj = adjust_day(_wo("easy", 376, 6), {"readiness": 30, "acwr": 1.0}, PACES)
    assert adj and adj["adjusted_run_type"] == "rest"

def test_mid_readiness_softens_quality_to_mp():
    adj = adjust_day(_wo("quality", 316), {"readiness": 48, "acwr": 1.0}, PACES)
    assert adj and adj["adjusted_run_type"] == "quality"
    assert adj["adjusted_target_pace_s"] == PACES["mp"]

def test_fresh_and_ahead_sharpens_quality():
    adj = adjust_day(_wo("quality", 316), {"readiness": 82, "acwr": 0.9, "recent_quality_hit": True, "downgrade_last_48h": False}, PACES)
    assert adj and adj["adjusted_target_pace_s"] == 306  # 10s sneller

def test_fresh_but_recent_downgrade_no_upgrade():
    adj = adjust_day(_wo("quality", 316), {"readiness": 82, "acwr": 0.9, "recent_quality_hit": True, "downgrade_last_48h": True}, PACES)
    assert adj is None

def test_good_signals_no_change():
    assert adjust_day(_wo("easy", 376, 6), {"readiness": 68, "acwr": 1.0}, PACES) is None

def test_rest_day_never_adjusted():
    assert adjust_day({"run_type": None, "title": "Rust"}, {"readiness": 20, "acwr": 2.0}, PACES) is None

def test_absorb_missed_marks_and_reschedules():
    rows = [
        {"date": "2026-07-13", "run_type": "quality", "done": False, "day_type": "run"},
        {"date": "2026-07-16", "run_type": "easy", "done": True, "day_type": "run"},
        {"date": "2026-07-18", "run_type": "long", "done": False, "day_type": "run"},
    ]
    out = absorb_missed(rows, today="2026-07-17")
    by = {r["date"]: r for r in out}
    assert by["2026-07-13"]["missed"] is True   # verleden, niet gedaan
    assert by["2026-07-16"]["missed"] is False   # gedaan
    assert by["2026-07-18"]["missed"] is False   # toekomst

def test_absorb_missed_empty():
    assert absorb_missed([], today="2026-07-17") == []
