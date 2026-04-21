#!/usr/bin/env python3
"""
NightWatch - Process pending overnight research queries.
Run via cron at 3 AM CDT. Queries Render backend, processes reports, delivers via Telegram.
"""
import os, sys, json, datetime, requests

API_KEY = os.environ.get("GROQ_API_KEY", "")
RENDER_URL = os.environ.get("NIGHTWATCH_BACKEND", "https://nightwatch-research.onrender.com")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram(msg: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram] Would send: {msg[:100]}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def synthesize_and_save(question: str) -> dict:
    """Run local research and LLM synthesis."""
    # Import the research module
    sys.path.insert(0, os.path.dirname(__file__))
    try:
        from main import run_investigation, call_openrouter
        report = run_investigation(question)
        return {"status": "complete", "report": report}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def main():
    print(f"[NightWatch] Runner starting at {datetime.datetime.utcnow()}")
    
    # Fetch pending queries from Render backend
    try:
        resp = requests.get(f"{RENDER_URL}/pending", timeout=10)
        pending = resp.json().get("pending", [])
    except Exception as e:
        print(f"[NightWatch] Could not reach backend: {e}")
        # Run local research instead
        send_telegram("⚠️ *NightWatch Backend unreachable — running local research*")
        return

    if not pending:
        send_telegram("🌙 *NightWatch is ready.* No pending queries. Sweet dreams.")
        print("[NightWatch] No pending queries.")
        return

    for query in pending:
        qid = query["query_id"]
        question = query["question"]
        print(f"[NightWatch] Processing: {qid} — {question}")
        send_telegram(f"🔍 *NightWatch is working:* `{question}`")

        try:
            resp = requests.get(f"{RENDER_URL}/report/{qid}", timeout=30)
            data = resp.json()
            if data.get("status") == "complete":
                report = data.get("report", "No report generated.")
                send_telegram(f"📬 *Report ready:*\n\n_{report[:800]}_")
            else:
                send_telegram(f"⏳ Query `{qid}` still processing. Check back in 30 min.")
        except Exception as e:
            print(f"[NightWatch] Error: {e}")
            send_telegram(f"❌ Error processing query `{qid}`: {e}")

    print(f"[NightWatch] Done at {datetime.datetime.utcnow()}")

if __name__ == "__main__":
    main()
