#!/usr/bin/env python3
import os
import sys
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # Python 3.9+
import urllib.parse
import urllib.request


def get_env(name, default=None, required=False):
    value = os.getenv(name, default)
    if required and not value:
        print(f"Missing required environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def get_access_token():
    client_id = get_env("ZOHO_CLIENT_ID", required=True)
    client_secret = get_env("ZOHO_CLIENT_SECRET", required=True)
    refresh_token = get_env("ZOHO_REFRESH_TOKEN", required=True)
    dc = get_env("ZOHO_DC", "accounts.zoho.in")

    token_url = f"https://{dc}/oauth/v2/token"
    params = {
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
    }

    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(token_url, data=data, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            js = json.loads(body)
    except Exception as e:
        print(f"Error getting access token: {e}", file=sys.stderr)
        sys.exit(1)

    access_token = js.get("access_token")
    if not access_token:
        print(f"Failed to get access token. Response: {js}", file=sys.stderr)
        sys.exit(1)

    return access_token


def calc_yesterday_hours():
    tz_name = get_env("ZOHO_TIMEZONE", "Asia/Kolkata")
    tz = ZoneInfo(tz_name)

    # now in local tz
    now = datetime.now(tz)
    yesterday = now - timedelta(days=1)

    # Date for Zoho: MM-DD-YYYY
    date_str = yesterday.strftime("%m-%d-%Y")

    start_str = get_env("ZOHO_TIME_START", "09:30")
    end_str = get_env("ZOHO_TIME_END", "18:30")

    start_hour, start_min = map(int, start_str.split(":"))
    end_hour, end_min = map(int, end_str.split(":"))

    start_dt = yesterday.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
    end_dt = yesterday.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)

    if end_dt <= start_dt:
        print("End time must be after start time", file=sys.stderr)
        sys.exit(1)

    diff = end_dt - start_dt
    total_minutes = diff.seconds // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    hours_str = f"{hours:02d}:{minutes:02d}"
    return date_str, hours_str


def add_time_log(access_token):
    portal_id = get_env("ZOHO_PORTAL_ID", required=True)
    project_id = get_env("ZOHO_PROJECT_ID", required=True)
    task_id = get_env("ZOHO_TASK_ID", required=True)
    user_id = get_env("ZOHO_USER_ID", required=False)
    bill_status = get_env("ZOHO_BILL_STATUS", "Billable")
    notes_prefix = get_env("ZOHO_NOTES_PREFIX", "GitHub auto log")

    date_str, hours_str = calc_yesterday_hours()
    print(f"Logging time for date={date_str}, hours={hours_str}")

    base_url = "https://projectsapi.zoho.com"
    endpoint = f"/restapi/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/logs/"
    url = base_url + endpoint

    params = {
        "date": date_str,          # MM-DD-YYYY
        "bill_status": bill_status,
        "hours": hours_str,        # hh:mm
        "notes": f"{notes_prefix} - {date_str}",
    }
    if user_id:
        params["owner"] = user_id  # Zoho user ID

    data = urllib.parse.urlencode(params).encode("utf-8")
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    }

    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            print("Zoho response status:", resp.status)
            print("Zoho response body:", body)
    except urllib.error.HTTPError as e:
        print("HTTP Error:", e.code, e.reason, file=sys.stderr)
        print(e.read().decode("utf-8"), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error calling Zoho Projects API: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    token = get_access_token()
    add_time_log(token)


if __name__ == "__main__":
    main()
