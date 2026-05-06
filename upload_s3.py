#!/usr/bin/env python3
"""
Fetches the SUB cinema schedule and uploads schedule.json to Yandex Object Storage.

Config is read from s3_config.json (not committed to git) or environment variables.

s3_config.json format:
{
  "aws_access_key_id":     "...",
  "aws_secret_access_key": "...",
  "endpoint_url":          "https://storage.yandexcloud.net",
  "region":                "ru-central1",
  "bucket":                "bancos-data",
  "key":                   "cartelera/schedule.json"
}
"""

import os, sys, json, subprocess
from pathlib import Path

# ── Load config ───────────────────────────────────────────────────────────
BASE = Path(__file__).parent
CONFIG_FILE = BASE / "s3_config.json"

cfg = {}
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = json.load(f)

def conf(key, env_var, default=""):
    return os.environ.get(env_var) or cfg.get(key) or default

ACCESS_KEY   = conf("aws_access_key_id",     "AWS_ACCESS_KEY_ID")
SECRET_KEY   = conf("aws_secret_access_key", "AWS_SECRET_ACCESS_KEY")
ENDPOINT     = conf("endpoint_url",          "S3_ENDPOINT",  "https://storage.yandexcloud.net")
REGION       = conf("region",                "S3_REGION",    "ru-central1")
BUCKET       = conf("bucket",                "S3_BUCKET",    "bancos-data")
KEY          = conf("key",                   "S3_KEY",       "cartelera/schedule.json")
LOCAL        = BASE / "schedule.json"

# ── Fetch schedule ────────────────────────────────────────────────────────
def fetch_and_save():
    print("Fetching schedule…")
    result = subprocess.run(
        [sys.executable, str(BASE / "fetch_schedule.py")],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("ERROR from fetch_schedule.py:", result.stderr, file=sys.stderr)
        sys.exit(1)
    data = json.loads(result.stdout)
    with open(LOCAL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  fetched_at : {data.get('fetched_at')}")
    print(f"  cinemas    : {len(data.get('cinemas', []))}")
    return data

# ── Upload to Yandex Object Storage ──────────────────────────────────────
def upload(data):
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError
    except ImportError:
        print("ERROR: boto3 not installed. Run: pip install boto3", file=sys.stderr)
        sys.exit(1)

    if not ACCESS_KEY or not SECRET_KEY:
        print("ERROR: S3 credentials not found. Add them to s3_config.json.", file=sys.stderr)
        sys.exit(1)

    s3 = boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        region_name=REGION,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        s3.put_object(
            Bucket=BUCKET,
            Key=KEY,
            Body=body,
            ContentType="application/json",
            CacheControl="max-age=3600",
            ACL="public-read",
        )
        url = f"{ENDPOINT}/{BUCKET}/{KEY}"
        print(f"Uploaded → {url}")
        return url
    except NoCredentialsError:
        print("ERROR: Invalid credentials.", file=sys.stderr)
        sys.exit(1)
    except ClientError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    data = fetch_and_save()
    upload(data)
