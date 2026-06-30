#!/usr/bin/env python3
"""Ingest JSON-bestanden uit output/<athlete>/ naar SQLite."""

import json
import sqlite3
import sys
from pathlib import Path

from db import DB_PATH, get_conn, init_db


def upsert_athlete(conn: sqlite3.Connection, athlete_id: str, display_name: str, panels: list) -> None:
    conn.execute(
        """
        INSERT INTO athletes (id, display_name, panels_config)
        VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            display_name  = excluded.display_name,
            panels_config = excluded.panels_config
        """,
        (athlete_id, display_name, json.dumps(panels)),
    )
    conn.commit()


def ingest_activities(conn: sqlite3.Connection, athlete_id: str, data: list) -> int:
    count = 0
    for a in data:
        date = (a.get("startTimeLocal") or "")[:10]
        conn.execute(
            """
            INSERT INTO activities (
                athlete_id, activity_id, date, name, type_key,
                distance_m, duration_s, avg_speed_mps, avg_hr, max_hr,
                hr_zone_1_s, hr_zone_2_s, hr_zone_3_s, hr_zone_4_s, hr_zone_5_s,
                aerobic_effect, anaerobic_effect, avg_cadence,
                training_load, bb_cost, avg_stride_cm, avg_gct_ms,
                avg_vert_osc_mm, avg_vert_ratio, aerobic_effect_msg,
                training_effect_label, avg_power
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(athlete_id, activity_id) DO UPDATE SET
                date=excluded.date, name=excluded.name, type_key=excluded.type_key,
                distance_m=excluded.distance_m, duration_s=excluded.duration_s,
                avg_speed_mps=excluded.avg_speed_mps, avg_hr=excluded.avg_hr,
                max_hr=excluded.max_hr,
                hr_zone_1_s=excluded.hr_zone_1_s, hr_zone_2_s=excluded.hr_zone_2_s,
                hr_zone_3_s=excluded.hr_zone_3_s, hr_zone_4_s=excluded.hr_zone_4_s,
                hr_zone_5_s=excluded.hr_zone_5_s,
                aerobic_effect=excluded.aerobic_effect,
                anaerobic_effect=excluded.anaerobic_effect,
                avg_cadence=excluded.avg_cadence,
                training_load=excluded.training_load, bb_cost=excluded.bb_cost,
                avg_stride_cm=excluded.avg_stride_cm, avg_gct_ms=excluded.avg_gct_ms,
                avg_vert_osc_mm=excluded.avg_vert_osc_mm,
                avg_vert_ratio=excluded.avg_vert_ratio,
                aerobic_effect_msg=excluded.aerobic_effect_msg,
                training_effect_label=excluded.training_effect_label,
                avg_power=excluded.avg_power
            """,
            (
                athlete_id,
                a.get("activityId"),
                date,
                a.get("activityName"),
                (a.get("activityType") or {}).get("typeKey"),
                a.get("distance"),
                a.get("duration"),
                a.get("averageSpeed"),
                a.get("averageHR"),
                a.get("maxHR"),
                a.get("hrTimeInZone_1"),
                a.get("hrTimeInZone_2"),
                a.get("hrTimeInZone_3"),
                a.get("hrTimeInZone_4"),
                a.get("hrTimeInZone_5"),
                a.get("aerobicTrainingEffect"),
                a.get("anaerobicTrainingEffect"),
                a.get("averageRunningCadenceInStepsPerMinute"),
                a.get("activityTrainingLoad"),
                a.get("differenceBodyBattery"),
                a.get("avgStrideLength"),
                a.get("avgGroundContactTime"),
                a.get("avgVerticalOscillation"),
                a.get("avgVerticalRatio"),
                a.get("aerobicTrainingEffectMessage"),
                a.get("trainingEffectLabel"),
                a.get("avgPower"),
            ),
        )
        count += 1
    conn.commit()
    return count


def ingest_daily_stats(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, row in data.items():
        if row is None:
            continue
        conn.execute(
            """
            INSERT INTO daily_stats (athlete_id, date, steps, active_calories, total_calories)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                steps=excluded.steps,
                active_calories=excluded.active_calories,
                total_calories=excluded.total_calories
            """,
            (athlete_id, date, row.get("totalSteps"), row.get("activeKilocalories"), row.get("totalKilocalories")),
        )
        count += 1
    conn.commit()
    return count


def ingest_daily_heart_rates(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, row in data.items():
        if row is None:
            continue
        conn.execute(
            """
            INSERT INTO daily_heart_rates (athlete_id, date, min_hr, max_hr, resting_hr)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                min_hr=excluded.min_hr, max_hr=excluded.max_hr, resting_hr=excluded.resting_hr
            """,
            (athlete_id, date, row.get("minHeartRate"), row.get("maxHeartRate"), row.get("restingHeartRate")),
        )
        count += 1
    conn.commit()
    return count


def ingest_body_battery(conn: sqlite3.Connection, athlete_id: str, data: list) -> int:
    count = 0
    for row in data:
        if row is None:
            continue
        conn.execute(
            """
            INSERT INTO body_battery (athlete_id, date, charged, drained)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                charged=excluded.charged, drained=excluded.drained
            """,
            (athlete_id, row.get("date"), row.get("charged"), row.get("drained")),
        )
        count += 1
    conn.commit()
    return count


def ingest_training_readiness(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, entries in data.items():
        if not entries:
            continue
        entry = entries[0] if isinstance(entries, list) else entries
        conn.execute(
            """
            INSERT INTO training_readiness (athlete_id, date, score, level, feedback_short)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                score=excluded.score, level=excluded.level, feedback_short=excluded.feedback_short
            """,
            (
                athlete_id,
                entry.get("calendarDate", date),
                entry.get("score"),
                entry.get("level"),
                entry.get("feedbackShort"),
            ),
        )
        count += 1
    conn.commit()
    return count


def ingest_vo2max_from_training_status(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    seen = set()
    count = 0
    for _, row in data.items():
        if not row:
            continue
        generic = (row.get("mostRecentVO2Max") or {}).get("generic") or {}
        date = generic.get("calendarDate")
        value = generic.get("vo2MaxValue")
        if date and value and date not in seen:
            seen.add(date)
            conn.execute(
                """
                INSERT INTO vo2max (athlete_id, date, vo2max)
                VALUES (?, ?, ?)
                ON CONFLICT(athlete_id, date) DO UPDATE SET vo2max=excluded.vo2max
                """,
                (athlete_id, date, value),
            )
            count += 1
    conn.commit()
    return count


def ingest_training_load_balance(conn: sqlite3.Connection, athlete_id: str, data: dict) -> int:
    count = 0
    for date, row in data.items():
        if row is None:
            continue

        acwr: dict = {}
        status_feedback = None
        status_map = (row.get("mostRecentTrainingStatus") or {}).get("latestTrainingStatusData") or {}
        for device_data in status_map.values():
            if device_data.get("primaryTrainingDevice"):
                acwr = device_data.get("acuteTrainingLoadDTO") or {}
                status_feedback = device_data.get("trainingStatusFeedbackPhrase")
                break

        bal: dict = {}
        balance_feedback = None
        balance_map = (
            (row.get("mostRecentTrainingLoadBalance") or {})
            .get("metricsTrainingLoadBalanceDTOMap") or {}
        )
        for device_data in balance_map.values():
            if device_data.get("primaryTrainingDevice"):
                bal = device_data
                balance_feedback = device_data.get("trainingBalanceFeedbackPhrase")
                break

        conn.execute(
            """
            INSERT INTO training_load_balance (
                athlete_id, date, acwr, acwr_percent, acwr_status,
                acute_load, chronic_load, chronic_min, chronic_max,
                aerobic_low, aerobic_high, anaerobic,
                aerobic_low_target_min, aerobic_low_target_max,
                aerobic_high_target_min, aerobic_high_target_max,
                anaerobic_target_min, anaerobic_target_max,
                balance_feedback, status_feedback
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(athlete_id, date) DO UPDATE SET
                acwr=excluded.acwr, acwr_percent=excluded.acwr_percent,
                acwr_status=excluded.acwr_status,
                acute_load=excluded.acute_load, chronic_load=excluded.chronic_load,
                chronic_min=excluded.chronic_min, chronic_max=excluded.chronic_max,
                aerobic_low=excluded.aerobic_low, aerobic_high=excluded.aerobic_high,
                anaerobic=excluded.anaerobic,
                aerobic_low_target_min=excluded.aerobic_low_target_min,
                aerobic_low_target_max=excluded.aerobic_low_target_max,
                aerobic_high_target_min=excluded.aerobic_high_target_min,
                aerobic_high_target_max=excluded.aerobic_high_target_max,
                anaerobic_target_min=excluded.anaerobic_target_min,
                anaerobic_target_max=excluded.anaerobic_target_max,
                balance_feedback=excluded.balance_feedback,
                status_feedback=excluded.status_feedback
            """,
            (
                athlete_id, date,
                acwr.get("dailyAcuteChronicWorkloadRatio"),
                acwr.get("acwrPercent"),
                acwr.get("acwrStatus"),
                acwr.get("dailyTrainingLoadAcute"),
                acwr.get("dailyTrainingLoadChronic"),
                acwr.get("minTrainingLoadChronic"),
                acwr.get("maxTrainingLoadChronic"),
                bal.get("monthlyLoadAerobicLow"),
                bal.get("monthlyLoadAerobicHigh"),
                bal.get("monthlyLoadAnaerobic"),
                bal.get("monthlyLoadAerobicLowTargetMin"),
                bal.get("monthlyLoadAerobicLowTargetMax"),
                bal.get("monthlyLoadAerobicHighTargetMin"),
                bal.get("monthlyLoadAerobicHighTargetMax"),
                bal.get("monthlyLoadAnaerobicTargetMin"),
                bal.get("monthlyLoadAnaerobicTargetMax"),
                balance_feedback,
                status_feedback,
            ),
        )
        count += 1
    conn.commit()
    return count


def ingest_activity_splits(conn: sqlite3.Connection, athlete_id: str, activity_id: int, data: dict) -> int:
    """Ingest lap splits voor één activiteit. data = JSON van get_activity_splits()."""
    laps = data.get("lapDTOs") or data.get("laps") or []
    count = 0
    for lap in laps:
        lap_index = lap.get("lapIndex")
        if lap_index is None:
            print(f"  WARNING: lap missing lapIndex, defaulting to 0", file=sys.stderr)
        split_num = (lap_index or 0) + 1
        conn.execute(
            """
            INSERT INTO activity_splits (athlete_id, activity_id, split_num, distance_m, duration_s, avg_hr, avg_speed_mps)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(athlete_id, activity_id, split_num) DO UPDATE SET
                distance_m=excluded.distance_m, duration_s=excluded.duration_s,
                avg_hr=excluded.avg_hr, avg_speed_mps=excluded.avg_speed_mps
            """,
            (
                athlete_id, activity_id, split_num,
                lap.get("distance"),
                lap.get("duration"),
                lap.get("averageHR"),
                lap.get("averageSpeed"),
            ),
        )
        count += 1
    conn.commit()
    return count


def run_ingest(athlete_id: str, display_name: str, output_dir: Path) -> None:
    init_db()
    conn = get_conn()

    default_panels = [
        "GoalBanner", "AttentionPoints", "HeroRow", "TrainingLoad",
        "WeekVolume", "TempoTrend", "ZoneDistribution", "RunEfficiency",
        "VO2MaxTrend", "RecentRuns", "SplitsPanel",
        "DailyStats", "RecoveryStrip",
    ]
    upsert_athlete(conn, athlete_id, display_name, default_panels)

    def load(fname):
        p = output_dir / fname
        return json.loads(p.read_text()) if p.exists() else None

    activities = load("activities.json") or []
    n_act = ingest_activities(conn, athlete_id, [a for a in activities if (a.get("activityType") or {}).get("typeKey") == "running"])
    print(f"  activities (runs): {n_act}")

    stats = load("stats.json") or {}
    print(f"  daily_stats: {ingest_daily_stats(conn, athlete_id, stats)}")

    heart_rates = load("heart_rates.json") or {}
    print(f"  daily_heart_rates: {ingest_daily_heart_rates(conn, athlete_id, heart_rates)}")

    body_battery = load("body_battery.json") or []
    print(f"  body_battery: {ingest_body_battery(conn, athlete_id, body_battery)}")

    tr = load("training_readiness.json") or {}
    print(f"  training_readiness: {ingest_training_readiness(conn, athlete_id, tr)}")

    ts = load("training_status.json") or {}
    print(f"  vo2max: {ingest_vo2max_from_training_status(conn, athlete_id, ts)}")
    print(f"  training_load_balance: {ingest_training_load_balance(conn, athlete_id, ts)}")

    splits_files = list(output_dir.glob("splits_*.json"))
    total_splits = 0
    for sf in splits_files:
        try:
            act_id = int(sf.stem.replace("splits_", ""))
            total_splits += ingest_activity_splits(conn, athlete_id, act_id, json.loads(sf.read_text()))
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  WARNING: Skipped {sf.name}: {e}", file=sys.stderr)
    print(f"  activity_splits: {total_splits} laps over {len(splits_files)} runs")

    print(f"\nDone → {DB_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--athlete", default="vriendin")
    parser.add_argument("--name", default="Vriendin")
    args = parser.parse_args()

    output_dir = Path("output") / args.athlete
    if not output_dir.exists():
        print(f"ERROR: {output_dir} niet gevonden")
        sys.exit(1)

    print(f"Ingesting {args.athlete}...")
    run_ingest(args.athlete, args.name, output_dir)
