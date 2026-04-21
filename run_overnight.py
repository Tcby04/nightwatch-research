"""
NightWatch Overnight Runner
Run via cron at 3 AM CDT. Processes pending queries and delivers reports.
"""
import os
import sys
import json
import datetime
import time
import requests as http

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

API_BASE = os.environ.get("NIGHTWATCH_API", "http://localhost:5000")

def send_report(query_id: str, report: str, channel: str = "email"):
    """Deliver report via configured channel."""
    # TODO: integrate with gog for email, or Telegram bot for messaging
    print(f"[NightWatch] Report ready for {query_id}: {report[:100]}...")
    return True

def process_pending():
    """Fetch and process all pending research queries."""
    try:
        resp = http.get(f"{API_BASE}/pending", timeout=10)
        pending = resp.json().get("pending", [])
    except Exception as e:
        print(f"[NightWatch] Could not reach API: {e}")
        return

    if not pending:
        print("[NightWatch] No pending queries. Sending ready ping.")
        return

    for query in pending:
        qid = query["query_id"]
        question = query["question"]
        print(f"[NightWatch] Processing: {qid} — {question}")

        try:
            resp = http.get(f"{API_BASE}/report/{qid}", timeout=10)
            data = resp.json()
            if data.get("status") == "complete":
                send_report(qid, data.get("report", ""))
            else:
                print(f"[NightWatch] Query {qid} not ready yet.")
        except Exception as e:
            print(f"[NightWatch] Error processing {qid}: {e}")

if __name__ == "__main__":
    print(f"[NightWatch] Overnight runner starting at {datetime.datetime.utcnow()}")
    process_pending()
    print(f"[NightWatch] Overnight runner done.")
