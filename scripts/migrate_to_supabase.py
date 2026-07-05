#!/usr/bin/env python3
"""One-time migration: garmin_coach.db → Supabase Postgres.

Usage:
    DATABASE_URL=postgresql://... python scripts/migrate_to_supabase.py
"""
import os
import sqlite3
from pathlib import Path

import psycopg2
import psycopg2.extras

SQLITE_PATH = Path(__file__).parent.parent / "garmin_coach.db"
DATABASE_URL = os.environ["DATABASE_URL"]

TABLES = [
    "athletes",
    "activities",
    "daily_stats",
    "daily_heart_rates",
    "body_battery",
    "training_readiness",
    "hrv",
    "sleep",
    "vo2max",
    "training_load_balance",
    "activity_splits",
]

TABLE_PKS = {
    "athletes": ["id"],
    "activities": ["athlete_id", "activity_id"],
    "daily_stats": ["athlete_id", "date"],
    "daily_heart_rates": ["athlete_id", "date"],
    "body_battery": ["athlete_id", "date"],
    "training_readiness": ["athlete_id", "date"],
    "hrv": ["athlete_id", "date"],
    "sleep": ["athlete_id", "date"],
    "vo2max": ["athlete_id", "date"],
    "training_load_balance": ["athlete_id", "date"],
    "activity_splits": ["athlete_id", "activity_id", "split_num"],
}


def migrate():
    if not SQLITE_PATH.exists():
        print(f"ERROR: {SQLITE_PATH} not found")
        return

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row

    dst = psycopg2.connect(DATABASE_URL)
    dst.autocommit = False

    try:
        with dst.cursor() as cur:
            for table in TABLES:
                rows = src.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    print(f"  {table}: 0 rows, skip")
                    continue

                cols = list(rows[0].keys())
                col_list = ", ".join(cols)
                placeholders = ", ".join(["%s"] * len(cols))
                conflict_cols = TABLE_PKS[table]
                update_cols = [c for c in cols if c not in conflict_cols]

                if update_cols:
                    update_set = ", ".join(f"{c}=EXCLUDED.{c}" for c in update_cols)
                    sql = (
                        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {update_set}"
                    )
                else:
                    sql = (
                        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({', '.join(conflict_cols)}) DO NOTHING"
                    )

                data = [tuple(r) for r in rows]
                psycopg2.extras.execute_batch(cur, sql, data, page_size=200)
                print(f"  {table}: {len(rows)} rows upserted")

        dst.commit()
        print("Migration complete.")
    except Exception as e:
        dst.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    migrate()
