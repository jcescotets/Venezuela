"""
garmin_mcp - MCP Server for Garmin Connect & FIT file analysis
Triathlon-focused tools for activity data, training metrics, and FIT parsing.
"""
import json
import os
import io
import tempfile
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path
import garth
import fitparse
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP
# ─── Server Init ────────────────────────────────────────────────────────────────
mcp = FastMCP("garmin_mcp")
# ─── Constants ──────────────────────────────────────────────────────────────────
GARMIN_DOMAIN = "garmin.com"
GARMIN_CONNECT_API = "connectapi"
FIT_SPORT_MAP = {
    0: "generic", 1: "running", 2: "cycling", 3: "transition",
    4: "fitness_equipment", 5: "swimming", 6: "basketball", 7: "soccer",
    8: "tennis", 9: "american_football", 10: "training", 11: "walking",
    12: "cross_country_skiing", 13: "alpine_skiing", 14: "snowboarding",
    15: "rowing", 16: "mountaineering", 17: "hiking", 18: "multisport",
    19: "paddling", 20: "flying", 21: "e_biking", 22: "motorcycling",
    23: "boating", 24: "driving", 25: "golf", 26: "hang_gliding",
    27: "horseback_riding", 28: "hunting", 29: "fishing",
    30: "inline_skating", 31: "rock_climbing", 32: "sailing",
    33: "ice_skating", 34: "sky_diving", 35: "snowshoeing",
    36: "snowmobiling", 37: "stand_up_paddleboarding",
    38: "surfing", 39: "wakeboarding", 40: "water_skiing",
    41: "kayaking", 42: "rafting", 43: "windsurfing",
    44: "kitesurfing", 45: "tactical", 46: "jumpmaster",
    47: "boxing", 48: "floor_climbing", 53: "diving",
    62: "yoga", 64: "pickleball", 65: "padel",
    254: "all",
}
# ─── Auth ────────────────────────────────────────────────────────────────────────
_client: Optional[garth.Client] = None
def _get_client() -> garth.Client:
    """Return authenticated Garmin client, initializing if needed."""
    global _client
    if _client is not None:
        return _client
    token_dir = os.environ.get("GARMIN_TOKEN_DIR", str(Path.home() / ".garth"))
    email = os.environ.get("GARMIN_EMAIL", "")
    password = os.environ.get("GARMIN_PASSWORD", "")
    client = garth.Client(domain=GARMIN_DOMAIN)
    # Try loading saved tokens first
    if os.path.exists(token_dir):
        try:
            client.load(token_dir)
            _client = client
            return client
        except Exception:
            pass
    # Fall back to credentials
    if not email or not password:
        raise ValueError(
            "Garmin credentials not configured. Set GARMIN_EMAIL and GARMIN_PASSWORD "
            "environment variables, or run garth.login() to save tokens to GARMIN_TOKEN_DIR."
        )
    client.login(email, password)
    os.makedirs(token_dir, exist_ok=True)
    client.dump(token_dir)
    _client = client
    return client
def _fmt_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return "N/A"
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"
def _fmt_pace(speed_ms: Optional[float]) -> str:
    """Convert m/s to min/km pace string."""
    if not speed_ms or speed_ms == 0:
        return "N/A"
    pace_s = 1000 / speed_ms
    m, s = divmod(int(pace_s), 60)
    return f"{m}:{s:02d} /km"
def _semicircles_to_degrees(sc: Optional[int]) -> Optional[float]:
    if sc is None:
        return None
    return sc * (180 / 2**31)
def _fit_value(val: Any) -> Any:
    """Clean FIT field value for JSON serialization."""
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    if hasattr(val, '__float__'):
        return float(val)
    return val
# ─── Input Models ────────────────────────────────────────────────────────────────
class ListActivitiesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    limit: int = Field(default=20, description="Number of activities to return", ge=1, le=100)
    start: int = Field(default=0, description="Offset for pagination", ge=0)
    sport_type: Optional[str] = Field(
        default=None,
        description="Filter by sport: running, cycling, swimming, multisport, walking, hiking, etc."
    )
class ActivityIdInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    activity_id: str = Field(..., description="Garmin Connect activity ID (e.g. '12345678901')")
class ParseFitInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    activity_id: str = Field(..., description="Garmin Connect activity ID to download and parse")
    include_records: bool = Field(
        default=False,
        description="Include per-second/per-lap data points (can be large). Default: summary only."
    )
    max_records: int = Field(
        default=500,
        description="Max number of record datapoints to return when include_records=True",
        ge=1, le=5000
    )
class TrainingLoadInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    days: int = Field(default=30, description="Look-back window in days", ge=7, le=90)
    sport_type: Optional[str] = Field(
        default=None,
        description="Filter by sport (optional)"
    )
# ─── Tools ───────────────────────────────────────────────────────────────────────
@mcp.tool(
    name="garmin_list_activities",
    annotations={
        "title": "List Garmin Activities",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def garmin_list_activities(params: ListActivitiesInput) -> str:
    """List recent activities from Garmin Connect with key metrics.
    Returns a summary list of activities including sport type, distance, duration,
    average HR, pace/speed, and TSS when available.
    Args:
        params: ListActivitiesInput with limit, start offset, and optional sport filter.
    Returns:
        str: JSON array of activity summaries.
    """
    try:
        client = _get_client()
        resp = client.get(
            GARMIN_CONNECT_API,
            "/activitylist-service/activities/search/activities",
            api=True,
            params={"limit": params.limit, "start": params.start}
        )
        activities = resp.json()
        results = []
        for a in activities:
            sport = a.get("activityType", {}).get("typeKey", "unknown")
            if params.sport_type and params.sport_type.lower() not in sport.lower():
                continue
            distance_m = a.get("distance", 0) or 0
            duration_s = a.get("duration", 0) or 0
            avg_speed = a.get("averageSpeed", 0) or 0
            results.append({
                "activity_id": str(a.get("activityId", "")),
                "name": a.get("activityName", ""),
                "sport": sport,
                "date": a.get("startTimeLocal", ""),
                "distance_km": round(distance_m / 1000, 2),
                "duration": _fmt_duration(duration_s),
                "avg_hr": a.get("averageHR"),
                "max_hr": a.get("maxHR"),
                "avg_pace": _fmt_pace(avg_speed) if sport in ("running", "walking") else None,
                "avg_speed_kmh": round(avg_speed * 3.6, 1) if avg_speed else None,
                "calories": a.get("calories"),
                "training_stress_score": a.get("trainingStressScore"),
                "aerobic_effect": a.get("aerobicTrainingEffect"),
                "anaerobic_effect": a.get("anaerobicTrainingEffect"),
                "elevation_gain_m": a.get("elevationGain"),
            })
        return json.dumps({
            "total_returned": len(results),
            "activities": results
        }, indent=2, default=str)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error fetching activities: {type(e).__name__}: {e}"
@mcp.tool(
    name="garmin_get_activity_detail",
    annotations={
        "title": "Get Activity Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def garmin_get_activity_detail(params: ActivityIdInput) -> str:
    """Get detailed metrics for a specific Garmin activity.
    Fetches extended data including HR zones, pace zones, splits, weather,
    power metrics (if available), and training effect details.
    Args:
        params: ActivityIdInput with the activity_id.
    Returns:
        str: JSON with full activity detail, splits, and zones.
    """
    try:
        client = _get_client()
        aid = params.activity_id
        # Main activity details
        detail = client.get(
            GARMIN_CONNECT_API,
            f"/activity-service/activity/{aid}",
            api=True,
        ).json()
        # HR zones
        try:
            hr_zones = client.get(
                GARMIN_CONNECT_API,
                f"/activity-service/activity/{aid}/hrTimeInZones",
                api=True,
            ).json()
        except Exception:
            hr_zones = None
        # Splits
        try:
            splits = client.get(
                GARMIN_CONNECT_API,
                f"/activity-service/activity/{aid}/splits",
                api=True,
            ).json()
        except Exception:
            splits = None
        summary = detail.get("summaryDTO", {})
        sport = detail.get("activityTypeDTO", {}).get("typeKey", "unknown")
        distance_m = summary.get("distance", 0) or 0
        result = {
            "activity_id": aid,
            "name": detail.get("activityName", ""),
            "sport": sport,
            "date": summary.get("startTimeLocal", ""),
            "distance_km": round(distance_m / 1000, 3),
            "duration": _fmt_duration(summary.get("elapsedDuration")),
            "moving_time": _fmt_duration(summary.get("movingDuration")),
            "avg_hr": summary.get("averageHR"),
            "max_hr": summary.get("maxHR"),
            "avg_speed_ms": summary.get("averageSpeed"),
            "avg_pace": _fmt_pace(summary.get("averageSpeed")) if "run" in sport else None,
            "max_speed_ms": summary.get("maxSpeed"),
            "calories": summary.get("calories"),
            "elevation_gain_m": summary.get("elevationGain"),
            "elevation_loss_m": summary.get("elevationLoss"),
            "avg_cadence": summary.get("averageBikingCadenceInRevPerMinute")
                           or summary.get("averageRunningCadenceInStepsPerMinute"),
            "avg_power_w": summary.get("avgPower"),
            "normalized_power_w": summary.get("normPower"),
            "training_stress_score": summary.get("trainingStressScore"),
            "intensity_factor": summary.get("intensityFactor"),
            "aerobic_effect": summary.get("aerobicTrainingEffect"),
            "anaerobic_effect": summary.get("anaerobicTrainingEffect"),
            "vo2max_estimate": summary.get("vO2MaxValue"),
            "hrv_weekly_avg": summary.get("hrvWeeklyAverage"),
            "weather": {
                "temp_c": summary.get("weatherTemp"),
                "humidity": summary.get("weatherHumidity"),
                "wind_speed": summary.get("windSpeed"),
            } if summary.get("weatherTemp") else None,
        }
        if hr_zones:
            result["hr_zones"] = hr_zones
        if splits:
            laps = splits.get("lapDTOs", [])
            result["laps"] = [
                {
                    "lap": i + 1,
                    "distance_km": round((lap.get("distance") or 0) / 1000, 3),
                    "duration": _fmt_duration(lap.get("duration")),
                    "avg_hr": lap.get("averageHR"),
                    "avg_pace": _fmt_pace(lap.get("averageSpeed")) if "run" in sport else None,
                    "avg_speed_kmh": round((lap.get("averageSpeed") or 0) * 3.6, 1),
                    "avg_power_w": lap.get("avgPower"),
                    "elevation_gain_m": lap.get("elevationGain"),
                }
                for i, lap in enumerate(laps[:50])  # Cap at 50 laps
            ]
        return json.dumps(result, indent=2, default=str)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error fetching activity {params.activity_id}: {type(e).__name__}: {e}"
@mcp.tool(
    name="garmin_parse_fit_file",
    annotations={
        "title": "Parse FIT File from Activity",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def garmin_parse_fit_file(params: ParseFitInput) -> str:
    """Download and parse the raw FIT file for a Garmin activity.
    Returns decoded FIT messages including session summary, lap data, and
    optionally per-record data points (GPS, HR, power, cadence at each second).
    Ideal for deep analysis of triathlon or cycling activities.
    Args:
        params: ParseFitInput with activity_id, include_records flag, and max_records limit.
    Returns:
        str: JSON with FIT session, laps, and optionally record datapoints.
    """
    try:
        client = _get_client()
        aid = params.activity_id
        # Download the FIT file
        response = client.get(
            GARMIN_CONNECT_API,
            f"/download-service/files/activity/{aid}",
            api=True,
        )
        # Garmin returns a zip with the .fit inside
        import zipfile
        fit_data = None
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            for name in zf.namelist():
                if name.endswith(".fit"):
                    fit_data = zf.read(name)
                    break
        if not fit_data:
            return "Error: No .fit file found in download archive."
        # Parse FIT
        fit = fitparse.FitFile(io.BytesIO(fit_data))
        sessions = []
        laps = []
        records = []
        events = []
        for msg in fit.get_messages():
            name = msg.name
            data = {f.name: _fit_value(f.value) for f in msg.fields if f.value is not None}
            if name == "session":
                # Convert semicircles
                for key in ("start_position_lat", "start_position_long",
                            "end_position_lat", "end_position_long"):
                    if key in data:
                        data[key] = _semicircles_to_degrees(data[key])
                sessions.append(data)
            elif name == "lap":
                for key in ("start_position_lat", "start_position_long",
                            "end_position_lat", "end_position_long"):
                    if key in data:
                        data[key] = _semicircles_to_degrees(data[key])
                laps.append(data)
            elif name == "record" and params.include_records:
                if "position_lat" in data:
                    data["position_lat"] = _semicircles_to_degrees(data["position_lat"])
                if "position_long" in data:
                    data["position_long"] = _semicircles_to_degrees(data["position_long"])
                records.append(data)
            elif name == "event":
                events.append(data)
        # Compute record statistics if we have them
        record_stats = None
        if params.include_records and records:
            def _stat(field):
                vals = [r[field] for r in records if field in r and r[field] is not None]
                if not vals:
                    return None
                return {"min": min(vals), "max": max(vals), "avg": round(sum(vals)/len(vals), 2)}
            record_stats = {
                "total_points": len(records),
                "heart_rate": _stat("heart_rate"),
                "power": _stat("power"),
                "cadence": _stat("cadence"),
                "speed": _stat("speed"),
                "altitude": _stat("altitude"),
                "temperature": _stat("temperature"),
            }
        result = {
            "activity_id": aid,
            "sessions": sessions,
            "laps": laps,
            "events": events[:20],  # Limit events
        }
        if params.include_records:
            result["record_stats"] = record_stats
            # Downsample records to max_records
            step = max(1, len(records) // params.max_records)
            result["records"] = records[::step][:params.max_records]
            result["records_note"] = (
                f"Showing {len(result['records'])} of {len(records)} total record points "
                f"(every {step}th point)"
            )
        return json.dumps(result, indent=2, default=str)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error parsing FIT file for activity {params.activity_id}: {type(e).__name__}: {e}"
@mcp.tool(
    name="garmin_get_training_load",
    annotations={
        "title": "Get Training Load & Readiness",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def garmin_get_training_load(params: TrainingLoadInput) -> str:
    """Analyze training load across recent activities: TSS, ATL, CTL trends.
    Aggregates activities over the specified window and computes:
    - Total load per sport
    - Acute (7d) vs Chronic (42d) Training Load proxy
    - Average aerobic/anaerobic effect
    - Volume by sport type
    Args:
        params: TrainingLoadInput with days window and optional sport filter.
    Returns:
        str: JSON with training load summary and per-sport breakdown.
    """
    try:
        client = _get_client()
        # Fetch enough activities to cover the window (approx 3/day max)
        limit = min(params.days * 3, 100)
        resp = client.get(
            GARMIN_CONNECT_API,
            "/activitylist-service/activities/search/activities",
            api=True,
            params={"limit": limit, "start": 0}
        )
        activities = resp.json()
        # Filter by date window
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=params.days)
        filtered = []
        for a in activities:
            start_str = a.get("startTimeLocal", "")
            try:
                act_date = datetime.fromisoformat(start_str.replace("Z", "+00:00").split("+")[0])
                if act_date < cutoff:
                    continue
            except Exception:
                continue
            sport = a.get("activityType", {}).get("typeKey", "unknown")
            if params.sport_type and params.sport_type.lower() not in sport.lower():
                continue
            filtered.append({
                "activity_id": str(a.get("activityId", "")),
                "date": start_str,
                "sport": sport,
                "distance_km": round((a.get("distance") or 0) / 1000, 2),
                "duration_s": a.get("duration") or 0,
                "tss": a.get("trainingStressScore"),
                "aerobic_effect": a.get("aerobicTrainingEffect"),
                "anaerobic_effect": a.get("anaerobicTrainingEffect"),
                "calories": a.get("calories"),
                "avg_hr": a.get("averageHR"),
            })
        if not filtered:
            return json.dumps({"message": f"No activities found in the last {params.days} days.", "activities": []})
        # Per-sport breakdown
        sport_summary: Dict[str, Any] = {}
        for a in filtered:
            s = a["sport"]
            if s not in sport_summary:
                sport_summary[s] = {
                    "count": 0, "total_distance_km": 0, "total_duration_h": 0,
                    "total_tss": 0, "tss_count": 0,
                    "avg_aerobic_effect": [], "avg_hr_list": []
                }
            ss = sport_summary[s]
            ss["count"] += 1
            ss["total_distance_km"] += a["distance_km"]
            ss["total_duration_h"] += a["duration_s"] / 3600
            if a["tss"]:
                ss["total_tss"] += a["tss"]
                ss["tss_count"] += 1
            if a["aerobic_effect"]:
                ss["avg_aerobic_effect"].append(a["aerobic_effect"])
            if a["avg_hr"]:
                ss["avg_hr_list"].append(a["avg_hr"])
        # Compute ATL (7-day) proxy
        from datetime import timedelta
        cutoff_7d = datetime.now() - timedelta(days=7)
        atl_acts = [a for a in filtered if a["date"] >= cutoff_7d.isoformat()]
        atl_tss = sum(a["tss"] or 0 for a in atl_acts)
        # Finalize sport summaries
        for s, ss in sport_summary.items():
            ae = ss.pop("avg_aerobic_effect")
            hr = ss.pop("avg_hr_list")
            tc = ss.pop("tss_count")
            ss["total_distance_km"] = round(ss["total_distance_km"], 2)
            ss["total_duration_h"] = round(ss["total_duration_h"], 2)
            ss["total_tss"] = round(ss["total_tss"], 1)
            ss["avg_aerobic_effect"] = round(sum(ae)/len(ae), 2) if ae else None
            ss["avg_hr"] = round(sum(hr)/len(hr)) if hr else None
        return json.dumps({
            "window_days": params.days,
            "total_activities": len(filtered),
            "total_tss": round(sum(a["tss"] or 0 for a in filtered), 1),
            "atl_7d_tss": round(atl_tss, 1),
            "total_distance_km": round(sum(a["distance_km"] for a in filtered), 2),
            "total_duration_h": round(sum(a["duration_s"] for a in filtered) / 3600, 2),
            "sport_breakdown": sport_summary,
            "recent_activities": filtered[:30],
        }, indent=2, default=str)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error fetching training load: {type(e).__name__}: {e}"
@mcp.tool(
    name="garmin_get_wellness",
    annotations={
        "title": "Get Daily Wellness Metrics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def garmin_get_wellness(params: ActivityIdInput) -> str:
    """Get daily wellness data for a specific date from Garmin Connect.
    Retrieves sleep score, HRV status, stress, steps, body battery,
    and resting heart rate for the date of the given activity or a date string.
    Args:
        params: ActivityIdInput — pass a date string like '2024-03-15' as activity_id.
    Returns:
        str: JSON with wellness metrics for that date.
    """
    try:
        client = _get_client()
        target_date = params.activity_id  # Reusing field as date input
        # Validate it looks like a date
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            return "Error: activity_id should be a date in YYYY-MM-DD format for this tool."
        wellness = {}
        # Sleep
        try:
            sleep = client.get(
                GARMIN_CONNECT_API,
                "/wellness-service/wellness/dailySleepData",
                api=True,
                params={"date": target_date}
            ).json()
            sd = sleep.get("dailySleepDTO", {})
            wellness["sleep"] = {
                "score": sd.get("sleepScores", {}).get("overall", {}).get("value"),
                "duration_h": round((sd.get("sleepTimeSeconds") or 0) / 3600, 2),
                "deep_h": round((sd.get("deepSleepSeconds") or 0) / 3600, 2),
                "rem_h": round((sd.get("remSleepSeconds") or 0) / 3600, 2),
                "light_h": round((sd.get("lightSleepSeconds") or 0) / 3600, 2),
                "awake_h": round((sd.get("awakeSleepSeconds") or 0) / 3600, 2),
                "avg_spo2": sd.get("averageSpO2Value"),
                "avg_respiration": sd.get("averageRespirationValue"),
            }
        except Exception as e:
            wellness["sleep"] = f"unavailable: {e}"
        # HRV
        try:
            hrv = client.get(
                GARMIN_CONNECT_API,
                f"/hrv-service/hrv/{target_date}",
                api=True,
            ).json()
            wellness["hrv"] = {
                "last_night": hrv.get("lastNight"),
                "weekly_avg": hrv.get("weeklyAvg"),
                "status": hrv.get("hrvSummary", {}).get("status"),
                "baseline_low": hrv.get("baseline", {}).get("lowUpper"),
                "baseline_high": hrv.get("baseline", {}).get("balancedHigh"),
            }
        except Exception as e:
            wellness["hrv"] = f"unavailable: {e}"
        # Body Battery & Stress
        try:
            stress = client.get(
                GARMIN_CONNECT_API,
                f"/wellness-service/wellness/dailyStress/{target_date}",
                api=True,
            ).json()
            wellness["stress"] = {
                "avg_stress": stress.get("avgStressLevel"),
                "max_stress": stress.get("maxStressLevel"),
                "rest_stress_duration_min": round((stress.get("restStressDuration") or 0) / 60),
                "low_stress_duration_min": round((stress.get("lowStressDuration") or 0) / 60),
                "medium_stress_duration_min": round((stress.get("mediumStressDuration") or 0) / 60),
                "high_stress_duration_min": round((stress.get("highStressDuration") or 0) / 60),
            }
        except Exception as e:
            wellness["stress"] = f"unavailable: {e}"
        # Steps & RHR
        try:
            daily = client.get(
                GARMIN_CONNECT_API,
                f"/usersummary-service/usersummary/daily/{target_date}",
                api=True,
                params={"calendarDate": target_date}
            ).json()
            wellness["daily_summary"] = {
                "steps": daily.get("totalSteps"),
                "step_goal": daily.get("dailyStepGoal"),
                "resting_hr": daily.get("restingHeartRate"),
                "calories_total": daily.get("totalKilocalories"),
                "calories_active": daily.get("activeKilocalories"),
                "floors_ascended": daily.get("floorsAscended"),
                "intensity_minutes": daily.get("moderateIntensityMinutes", 0) + daily.get("vigorousIntensityMinutes", 0),
                "body_battery_high": daily.get("bodyBatteryHighestValue"),
                "body_battery_low": daily.get("bodyBatteryLowestValue"),
            }
        except Exception as e:
            wellness["daily_summary"] = f"unavailable: {e}"
        return json.dumps({"date": target_date, **wellness}, indent=2, default=str)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error fetching wellness data: {type(e).__name__}: {e}"
# ─── Entry Point ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
