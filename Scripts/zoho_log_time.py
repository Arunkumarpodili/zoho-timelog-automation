#!/usr/bin/env python3
import os
import sys
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta


def get_env(name):
    value = os.getenv(name)
    if not value:
        print(f"Missing environment variable: {name}")
        sys.exit(1)
    return value


def get_access_token():
    url = f"https://{get_env('ZOHO_DC')}/oauth/v2/token"

    data = urllib.parse.urlencode({
        "refresh_token": get_env("ZOHO_REFRESH_TOKEN"),
        "client_id": get_env("ZOHO_CLIENT_ID"),
        "client_secret": get_env("ZOHO_CLIENT_SECRET"),
        "grant_type": "refresh_token",
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
    except Exception as e:
        print("Error while requesting access token:", e)
        sys.exit(1)

    if "access_token" not in result:
        print("Failed to get access token. Response:", result)
        sys.exit(1)

    return result["access_token"]


def calculate_hours():
    # You are logging fixed hours: 09:30–18:30 = 9 hours
    return "09:00"


def get_yesterday_date():
    tz = os.getenv("ZOHO_TIMEZONE", "Asia/Kolkata")

    # Not importing zoneinfo to avoid timezone crash in GitHub
    now = datetime.utcnow() + timedelta(hours=5, minutes=30)  # IST offset
    yesterday = now - timedelta(days=1)

    return yesterday.strftime("%m-%d-%Y")


def log_time(token):
    portal = get_env("ZOHO_PORTAL_ID")
    project_id = get_env("ZOHO_PROJECT_ID")
    task_id = get_env("ZOHO_TASK_ID")

    url = f"https://projectsapi.zoho.com/restapi/portal/{portal}/projects/{project_id}/tasks/{task_id}/logs/"

    payload = urllib.parse.urlencode({
        "date": get_yesterday_date(),
        "hours": calculate_hours(),
        "bill_status": os.getenv("ZOHO_BILL_STATUS", "Billable"),
        "notes": os.getenv("ZOHO_NOTES_PREFIX", "POC project implimentation on PLGJ for CORTEX AI"),
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Zoho-oauthtoken {token}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req) as resp:
            output = resp.read().decode()
            print("SUCCESS:", output)
    except urllib.error.HTTPError as e:
        print("HTTP ERROR:", e.code)
        print(e.read().decode())
        sys.exit(1)
    except Exception as e:
        print("UNKNOWN ERROR:", e)
        sys.exit(1)


if __name__ == "__main__":
    access_token = get_access_token()
    log_time(access_token)
