"""
NightWatch Research Engine
Flask app that accepts a research query, runs investigation, delivers report.
"""
import os
import json
import uuid
import datetime
import requests
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def save_query(query_id: str, data: dict):
    path = os.path.join(DATA_DIR, f"{query_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_query(query_id: str):
    path = os.path.join(DATA_DIR, f"{query_id}.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def list_pending_queries():
    pending = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".json"):
            q = load_query(fname.replace(".json", ""))
            if q.get("status") == "pending":
                pending.append(q)
    return pending


def call_openrouter(prompt: str, model: str = "openai/gpt-4o") -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://never-sleep.ai",
        "X-Title": "Never Sleep - NightWatch",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }
    resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def synthesize_with_llm(raw_findings: dict, question: str) -> str:
    """Use LLM to turn raw findings into a structured report."""
    findings_str = json.dumps(raw_findings, indent=2)
    prompt = f"""You are NightWatch — an AI intelligence analyst. You investigated the following question:

QUESTION: {question}

You gathered the following raw data:
{findings_str}

Write a compelling, structured research report with these sections:
- Executive Summary (2-3 sentences)
- Key Findings (3-5 bullet points with specific details)
- Risks & Red Flags
- Opportunities & Recommendations

Be specific. No vague corporate language. This is a real intelligence deliverable.
"""
    return call_openrouter(prompt, model="openai/gpt-4o")


def gather_web_data(url: str, query: str) -> dict:
    """Use Playwright to gather content from a URL."""
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            text = page.inner_text("body")
            # Trim to first 4000 chars to avoid token overflow
            results["text"] = text[:4000]
            results["url"] = url
            results["title"] = page.title()[:200]
        except Exception as e:
            results["error"] = str(e)
        finally:
            browser.close()
    return results


def investigate_company(company_name: str) -> dict:
    """Run a basic company intelligence investigation."""
    findings = {
        "company": company_name,
        "timestamp": str(datetime.datetime.utcnow()),
        "sources": [],
    }

    # Try news search
    news_urls = [
        f"https://news.google.com/rss/search?q={requests.utils.quote(company_name)}&hl=en-US&gl=US&ceid=US:en",
    ]
    for url in news_urls:
        try:
            data = gather_web_data(url, company_name)
            if "text" in data:
                findings["news"] = data["text"][:3000]
                findings["sources"].append(url)
        except Exception:
            pass

    # Try Crunchbase-style domain lookup
    domain = f"{company_name.lower().replace(' ', '')}.com"
    try:
        data = gather_web_data(f"https://{domain}", company_name)
        if "text" in data:
            findings["website"] = {
                "title": data.get("title"),
                "snippet": data["text"][:1000],
                "url": f"https://{domain}",
            }
            findings["sources"].append(f"https://{domain}")
    except Exception:
        pass

    # Try LinkedIn search
    try:
        data = gather_web_data(
            f"https://www.google.com/search?q={requests.utils.quote(company_name + ' LinkedIn company')}&num=3",
            company_name
        )
        if "text" in data:
            findings["linkedin_signals"] = data["text"][:2000]
            findings["sources"].append("google search")
    except Exception:
        pass

    return findings


def investigate_market(market_query: str) -> dict:
    """Run a market research investigation."""
    findings = {
        "market": market_query,
        "timestamp": str(datetime.datetime.utcnow()),
        "sources": [],
    }

    # News search for market
    try:
        data = gather_web_data(
            f"https://news.google.com/rss/search?q={requests.utils.quote(market_query)}&hl=en-US&gl=US&ceid=US:en",
            market_query
        )
        if "text" in data:
            findings["news"] = data["text"][:3000]
            findings["sources"].append("google news")
    except Exception:
        pass

    # Google search for market overview
    try:
        data = gather_web_data(
            f"https://www.google.com/search?q={requests.utils.quote(market_query + ' market size trends 2024 2025')}&num=5",
            market_query
        )
        if "text" in data:
            findings["market_overview"] = data["text"][:3000]
            findings["sources"].append("google search")
    except Exception:
        pass

    return findings


def run_investigation(question: str) -> str:
    """Main investigation logic — routes to appropriate research path."""
    q_lower = question.lower()

    if any(kw in q_lower for kw in ["company", "competitor", "acme", "corp", "startup", "llc"]):
        # Try to extract company name (simple heuristic)
        words = question.split()
        # Use first meaningful word as company proxy
        company = words[2] if len(words) > 2 else question.split("?")[0].split()[-1]
        findings = investigate_company(company)
    elif any(kw in q_lower for kw in ["market", "industry", "fintech", "saas", "trends"]):
        findings = investigate_market(question)
    else:
        # Generic investigation via Google search
        findings = {"raw_search": question}
        try:
            data = gather_web_data(
                f"https://www.google.com/search?q={requests.utils.quote(question)}&num=5",
                question
            )
            if "text" in data:
                findings["google_results"] = data["text"][:3000]
        except Exception:
            findings["error"] = "Could not gather data"

    # Synthesize findings into report
    report = synthesize_with_llm(findings, question)
    return report


# ─── ROUTES ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return jsonify({
        "service": "NightWatch Research Engine",
        "status": "operational",
        "version": "1.0",
        "endpoints": ["/submit", "/report/<query_id>", "/status/<query_id>", "/pending"]
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": str(datetime.datetime.utcnow())})


@app.route("/submit", methods=["POST"])
def submit_query():
    """Accept a research question. Returns query_id immediately."""
    data = request.get_json()
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400

    query_id = str(uuid.uuid4())[:8]
    query_record = {
        "query_id": query_id,
        "question": question,
        "status": "pending",
        "submitted_at": str(datetime.datetime.utcnow()),
        "report": None,
    }
    save_query(query_id, query_record)

    # Run investigation immediately (for demo/prototype)
    try:
        report = run_investigation(question)
        query_record["status"] = "complete"
        query_record["report"] = report
        query_record["completed_at"] = str(datetime.datetime.utcnow())
    except Exception as e:
        query_record["status"] = "error"
        query_record["error"] = str(e)

    save_query(query_id, query_record)
    return jsonify(query_record)


@app.route("/report/<query_id>")
def get_report(query_id):
    """Fetch the research report for a completed query."""
    query = load_query(query_id)
    if not query:
        return jsonify({"error": "query not found"}), 404
    return jsonify(query)


@app.route("/status/<query_id>")
def get_status(query_id):
    """Check status of a research query."""
    query = load_query(query_id)
    if not query:
        return jsonify({"error": "query not found"}), 404
    return jsonify({
        "query_id": query_id,
        "status": query.get("status"),
        "submitted_at": query.get("submitted_at"),
    })


@app.route("/pending")
def list_pending():
    """List all pending research queries."""
    return jsonify({"pending": list_pending_queries()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
