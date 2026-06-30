#!/usr/bin/env python3
"""Pull N days of Garmin Connect data for one athlete."""

import argparse
import getpass
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from garminconnect import Garmin


def get_client(athlete: str, email: str, password: str) -> Garmin:
    tokenstore = Path(".garmin_tokens") / athlete
    tokenstore.mkdir(parents=True, exist_ok=True)

    # Try cached tokens first
    if any(tokenstore.iterdir()) if tokenstore.exists() else False:
        try:
            client = Garmin()
            client.login(str(tokenstore))
            print(f"[auth] token login OK ({athlete})")
            return client
        except Exception:
            pass

    # Fresh login — garth handles MFA prompt internally if needed
    print(f"[auth] fresh login for '{athlete}'...")
    client = Garmin(email, password)
    client.login()
    client.garth.dump(str(tokenstore))
    print(f"[auth] tokens saved → {tokenstore}/")
    return client


def fetch(label: str, fn, *args, **kwargs):
    try:
        result = fn(*args, **kwargs)
        print(f"  ✓ {label}")
        return result
    except Exception as exc:
        print(f"  ✗ {label}: {exc}")
        return None


def fetch_per_day(label: str, fn, days: list[date], *args, **kwargs) -> dict:
    results = {}
    for d in days:
        ds = d.isoformat()
        data = fetch(f"{label} {ds}", fn, ds, *args, **kwargs)
        results[ds] = data
    return results


def main():
    parser = argparse.ArgumentParser(description="Pull Garmin data for one athlete.")
    parser.add_argument("--athlete", default="vriendin", help="Athlete name (used as folder)")
    parser.add_argument("--days", type=int, default=7, help="Number of days to fetch")
    args = parser.parse_args()

    email = os.environ.get("GARMIN_EMAIL") or input("Garmin email: ")
    password = os.environ.get("GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")

    client = get_client(args.athlete, email, password)

    today = date.today()
    start = today - timedelta(days=args.days - 1)
    days = [start + timedelta(days=i) for i in range(args.days)]
    start_str = start.isoformat()
    end_str = today.isoformat()

    out = Path("output") / args.athlete
    out.mkdir(parents=True, exist_ok=True)

    print(f"\nFetching {args.days} days ({start_str} → {end_str}) for '{args.athlete}'...\n")

    # --- Range endpoints ---
    activities = fetch("activities", client.get_activities_by_date, start_str, end_str)
    body_battery = fetch("body_battery", client.get_body_battery, start_str, end_str)

    # --- Splits per hardloopactiviteit ---
    running_ids = [
        a["activityId"]
        for a in (activities or [])
        if (a.get("activityType") or {}).get("typeKey") == "running"
    ]
    print(f"\nFetching splits for {len(running_ids)} runs...")
    for act_id in running_ids:
        splits = fetch(f"splits {act_id}", client.get_activity_splits, act_id)
        if splits is not None:
            (out / f"splits_{act_id}.json").write_text(
                json.dumps(splits, indent=2, ensure_ascii=False)
            )

    # --- Per-day endpoints ---
    stats             = fetch_per_day("stats",              client.get_stats,                days)
    heart_rates       = fetch_per_day("heart_rates",        client.get_heart_rates,          days)
    sleep             = fetch_per_day("sleep",              client.get_sleep_data,           days)
    hrv               = fetch_per_day("hrv",                client.get_hrv_data,             days)
    training_readiness = fetch_per_day("training_readiness", client.get_training_readiness,  days)
    training_status   = fetch_per_day("training_status",    client.get_training_status,      days)

    full_name = fetch("full_name", client.get_full_name)

    # --- Write JSON ---
    files = {
        "activities.json":          activities,
        "body_battery.json":        body_battery,
        "stats.json":               stats,
        "heart_rates.json":         heart_rates,
        "sleep.json":               sleep,
        "hrv.json":                 hrv,
        "training_readiness.json":  training_readiness,
        "training_status.json":     training_status,
    }

    for filename, data in files.items():
        if data is not None:
            (out / filename).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # --- Summary ---
    name = full_name or args.athlete
    print(f"\n{'='*50}")
    print(f"  {name}  |  {start_str} → {end_str}")
    print(f"{'='*50}")

    act_list = activities or []
    if act_list:
        print(f"Activities ({len(act_list)}):")
        for a in sorted(act_list, key=lambda x: x.get("startTimeLocal", "")):
            dt     = (a.get("startTimeLocal") or "?")[:10]
            atype  = (a.get("activityType") or {}).get("typeKey", "?")
            aname  = a.get("activityName", "?")
            dist_m = a.get("distance") or 0
            dur_s  = a.get("duration") or 0
            hr     = a.get("averageHR") or "-"
            print(f"  {dt}  {atype:<14}  {aname:<30}  "
                  f"{dist_m/1000:5.1f}km  {dur_s/60:4.0f}min  HR:{hr}")
    else:
        print("No activities found in this period.")

    print(f"\nOutput → {out.resolve()}/")


if __name__ == "__main__":
    main()
