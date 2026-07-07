import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from coach_rules import duiding_readiness, duiding_load, duiding_run


def test_duiding_readiness_high():
    msg = duiding_readiness({"score": 82})
    assert "goed" in msg.lower() or "klaar" in msg.lower()


def test_duiding_readiness_low_mentions_rust():
    msg = duiding_readiness({"score": 35})
    assert "rust" in msg.lower() or "herstel" in msg.lower()


def test_duiding_load_high_warns():
    msg = duiding_load({"acwr": 1.6})
    assert "hoog" in msg.lower() or "blessure" in msg.lower()


def test_duiding_load_optimal():
    msg = duiding_load({"acwr": 1.0})
    assert "optimaal" in msg.lower() or "veilig" in msg.lower()


def test_duiding_run_negative_split():
    msg = duiding_run({"splits_pace": [324, 315, 306, 302, 294]})
    assert "negative split" in msg.lower() or "sneller" in msg.lower()


def test_duiding_run_handles_missing_data():
    assert isinstance(duiding_run({}), str)
    assert isinstance(duiding_readiness({}), str)
    assert isinstance(duiding_load({}), str)


from coach_rules import duiding_workout

def test_duiding_workout_variants():
    assert isinstance(duiding_workout("long", "build"), str)
    assert "lang" in duiding_workout("long", "build").lower()
    assert "taper" in duiding_workout("easy", "taper").lower() or "herstel" in duiding_workout("easy", "taper").lower()
    assert isinstance(duiding_workout("quality", "peak"), str)
