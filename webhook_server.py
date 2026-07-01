"""
Devin Automation Webhook Server
================================
Listens for GitHub issue events and automatically starts a Devin session
to remediate each issue. Posts status updates back to the GitHub issue
thread and tracks all sessions in a live dashboard.

Flow:
  GitHub issue opened/reopened
    → /webhook receives POST from GitHub
    → create_devin_session() calls the Devin API
    → post_github_comment() posts 🟡 Working on the issue
    → sessions.json records the session

  Devin opens a PR
    → /webhook receives pull_request.opened from GitHub
    → handle_pr_opened() matches PR back to originating issue
    → post_github_comment() posts 🟢 PR Ready on the issue
    → sessions.json updated with time_to_pr_minutes

  PR merged
    → /webhook receives pull_request.closed + merged=true
    → handle_pr_merged() closes the originating GitHub issue
    → posts ✅ resolution comment with time-to-resolution

Observability endpoints:
  /status   — live HTML dashboard (auto-refreshes every 30s)
  /metrics  — machine-readable JSON for Datadog/Grafana/PagerDuty
  /health   — uptime check with session count

Telemetry stored per session:
  started_at, updated_at, time_to_pr_minutes, time_to_merge_minutes
"""

import hmac
import hashlib
import json
import os
import re
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

DEVIN_API_KEY = os.environ.get("DEVIN_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
# Secret shared with GitHub webhook settings to verify payloads are authentic
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "superset-webhook-secret")
GITHUB_REPO = "lochenger/superset"
STATE_FILE = "sessions.json"


# ---------- Persistence ----------
# Sessions are kept in memory for speed but written to disk on every change
# so the dashboard and metrics survive server restarts.

def load_sessions():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_sessions(sessions):
    with open(STATE_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


sessions = load_sessions()


# ---------- Helpers ----------

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def minutes_since(started_at_str):
    """Returns integer minutes elapsed since started_at_str."""
    try:
        started = datetime.strptime(started_at_str, "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - started).total_seconds() // 60)
    except Exception:
        return 0


def elapsed(started_at_str):
    """Human-readable elapsed time — shown in the dashboard status column."""
    minutes = minutes_since(started_at_str)
    if minutes < 1:
        return "< 1 min"
    if minutes < 60:
        return f"{minutes} min"
    return f"{minutes // 60}h {minutes % 60}m"


def verify_signature(payload_body, signature_header):
    """Reject requests that didn't come from GitHub — prevents spoofed webhooks."""
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def post_github_comment(issue_number, body):
    """Post a comment on a GitHub issue — used for status updates throughout the lifecycle."""
    if not GITHUB_TOKEN:
        print("[!] GITHUB_TOKEN not set — skipping issue comment")
        return
    requests.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}/comments",
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"body": body},
    )


def close_github_issue(issue_number):
    """Close a GitHub issue — called automatically when Devin's PR is merged."""
    if not GITHUB_TOKEN:
        return
    requests.patch(
        f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}",
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"},
        json={"state": "closed"},
    )


def make_session_record(issue_number, issue_title, issue_url, status, session_id=None, session_url="#"):
    """Single place to build a session record — avoids copy-paste between success and error paths."""
    return {
        "issue_number": issue_number,
        "issue_title": issue_title,
        "issue_url": issue_url,
        "session_id": session_id,
        "session_url": session_url,
        "status": status,
        "pr_number": None,
        "pr_url": None,
        "started_at": now(),
        "updated_at": now(),
        "time_to_pr_minutes": None,
        "time_to_merge_minutes": None,
    }


def create_devin_session(issue_title, issue_body, issue_url, issue_number):
    """Call the Devin API to start a session. Returns (status_code, response_json)."""
    prompt = f"""You are working on the GitHub repository {GITHUB_REPO}.

A new issue has been filed that needs remediation:

Issue #{issue_number}: {issue_title}
URL: {issue_url}

Details:
{issue_body}

Please:
1. Clone or use the repository at https://github.com/{GITHUB_REPO}
2. Investigate the issue described above
3. Implement the fix
4. Open a pull request with your changes, referencing issue #{issue_number} in the PR description
"""
    response = requests.post(
        "https://api.devin.ai/v1/sessions",
        headers={"Authorization": f"Bearer {DEVIN_API_KEY}", "Content-Type": "application/json"},
        json={"prompt": prompt},
    )
    return response.status_code, response.json()


# ---------- Webhook Routes ----------

@app.route("/webhook", methods=["POST"])
def webhook():
    # Drop anything that doesn't have a valid GitHub signature
    if not verify_signature(request.data, request.headers.get("X-Hub-Signature-256")):
        return jsonify({"error": "Invalid signature"}), 401

    event = request.headers.get("X-GitHub-Event")
    payload = request.json

    # "reopened" retriggers automation so failed issues can be retried without cloning
    if event == "issues" and payload.get("action") in ("opened", "reopened"):
        return handle_issue_opened(payload)

    if event == "pull_request" and payload.get("action") == "opened":
        return handle_pr_opened(payload)

    # Auto-close the issue and record merge time when Devin's PR is merged
    if event == "pull_request" and payload.get("action") == "closed":
        if payload["pull_request"].get("merged"):
            return handle_pr_merged(payload)

    return jsonify({"status": "ignored"}), 200


def handle_issue_opened(payload):
    issue = payload["issue"]
    issue_number, issue_title = issue["number"], issue["title"]
    issue_body, issue_url = issue.get("body") or "", issue["html_url"]

    print(f"\n[+] Issue #{issue_number}: {issue_title}")
    status_code, devin_response = create_devin_session(issue_title, issue_body, issue_url, issue_number)

    if status_code == 200:
        session_id = devin_response.get("session_id", "unknown")
        session_url = devin_response.get("url", "unknown")

        sessions[str(issue_number)] = make_session_record(
            issue_number, issue_title, issue_url, "working", session_id, session_url
        )
        save_sessions(sessions)

        post_github_comment(issue_number, (
            f"🤖 **Devin session started automatically for this issue.**\n\n"
            f"| Field | Value |\n|---|---|\n"
            f"| **Status** | 🟡 Working |\n"
            f"| **Session** | [{session_url}]({session_url}) |\n"
            f"| **Session ID** | `{session_id}` |\n"
            f"| **Triggered by** | Issue opened event (webhook) |\n"
            f"| **Started** | {now()} |\n\n"
            f"Devin is investigating and will open a pull request with the fix."
        ))
        print(f"[+] Session started: {session_url}")
        return jsonify({"status": "success", "issue": issue_number, "session_id": session_id}), 200

    else:
        sessions[str(issue_number)] = make_session_record(
            issue_number, issue_title, issue_url, "error"
        )
        save_sessions(sessions)
        post_github_comment(issue_number, (
            f"❌ **Devin automation failed to start a session.**\n\n"
            f"Error: `{devin_response}`\n\nPlease review and retry manually."
        ))
        return jsonify({"status": "error", "devin_response": devin_response}), 500


def handle_pr_opened(payload):
    pr = payload["pull_request"]
    pr_number, pr_title = pr["number"], pr["title"]
    pr_url, pr_author = pr["html_url"], pr["user"]["login"]
    pr_body = pr.get("body") or ""

    # Only process PRs opened by the Devin bot
    if "devin" not in pr_author.lower():
        return jsonify({"status": "ignored", "reason": "not a Devin PR"}), 200

    # Devin writes "Closes #N" in the PR body — use that to find the originating issue
    match = re.search(r'(?:Closes|Fixes|Resolves)\s+#(\d+)', pr_body, re.IGNORECASE)
    issue_number = int(match.group(1)) if match else None

    if issue_number and str(issue_number) in sessions:
        # Record time-to-PR for the /metrics endpoint
        ttp = minutes_since(sessions[str(issue_number)]["started_at"])
        sessions[str(issue_number)].update({
            "status": "pr_ready",
            "pr_number": pr_number,
            "pr_url": pr_url,
            "updated_at": now(),
            "time_to_pr_minutes": ttp,
        })
        save_sessions(sessions)
        post_github_comment(issue_number, (
            f"🟢 **Devin opened a pull request for this issue.**\n\n"
            f"| Field | Value |\n|---|---|\n"
            f"| **Status** | 🟢 PR Ready for Review |\n"
            f"| **Pull Request** | [#{pr_number} — {pr_title}]({pr_url}) |\n"
            f"| **Time to PR** | {ttp} min |\n"
            f"| **Author** | @{pr_author} |\n"
            f"| **Updated** | {now()} |\n\n"
            f"Please review the pull request and merge when satisfied."
        ))
        print(f"[+] Issue #{issue_number} → PR Ready in {ttp} min (PR #{pr_number})")

    return jsonify({"status": "success", "pr": pr_number}), 200


def handle_pr_merged(payload):
    """When Devin's PR is merged: record time-to-merge, post resolution comment, close issue."""
    pr = payload["pull_request"]
    pr_number, pr_title = pr["number"], pr["title"]
    pr_author = pr["user"]["login"]

    if "devin" not in pr_author.lower():
        return jsonify({"status": "ignored", "reason": "not a Devin PR"}), 200

    # Find originating issue from sessions
    issue_number = next(
        (int(k) for k, v in sessions.items() if v.get("pr_number") == pr_number),
        None
    )

    if issue_number and str(issue_number) in sessions:
        ttm = minutes_since(sessions[str(issue_number)]["started_at"])
        sessions[str(issue_number)].update({
            "status": "merged",
            "updated_at": now(),
            "time_to_merge_minutes": ttm,
        })
        save_sessions(sessions)

        post_github_comment(issue_number, (
            f"✅ **Issue resolved — PR #{pr_number} was merged.**\n\n"
            f"| Field | Value |\n|---|---|\n"
            f"| **Status** | ✅ Merged |\n"
            f"| **Pull Request** | [#{pr_number} — {pr_title}]({pr['html_url']}) |\n"
            f"| **Time to resolution** | {ttm} min |\n"
            f"| **Merged at** | {now()} |\n\n"
            f"This issue was automatically closed by the Devin automation."
        ))
        close_github_issue(issue_number)
        print(f"[+] Issue #{issue_number} merged and closed in {ttm} min")

    return jsonify({"status": "success", "pr": pr_number}), 200


# ---------- Metrics Endpoint ----------
# Machine-readable JSON for external observability tools (Datadog, Grafana, PagerDuty).
# An engineering leader's ops team would scrape this rather than reading the HTML dashboard.

@app.route("/metrics", methods=["GET"])
def metrics():
    total = len(sessions)
    working = sum(1 for s in sessions.values() if s["status"] == "working")
    pr_ready = sum(1 for s in sessions.values() if s["status"] == "pr_ready")
    merged = sum(1 for s in sessions.values() if s["status"] == "merged")
    errors = sum(1 for s in sessions.values() if s["status"] == "error")

    # Average time-to-PR across all sessions that completed
    ttp_values = [s["time_to_pr_minutes"] for s in sessions.values() if s.get("time_to_pr_minutes")]
    avg_ttp = round(sum(ttp_values) / len(ttp_values), 1) if ttp_values else None

    # Average time-to-merge across all merged sessions
    ttm_values = [s["time_to_merge_minutes"] for s in sessions.values() if s.get("time_to_merge_minutes")]
    avg_ttm = round(sum(ttm_values) / len(ttm_values), 1) if ttm_values else None

    resolved = pr_ready + merged
    return jsonify({
        "repo": GITHUB_REPO,
        "total_sessions": total,
        "working": working,
        "pr_ready": pr_ready,
        "merged": merged,
        "errors": errors,
        "success_rate": round(resolved / total, 2) if total > 0 else 0,
        "avg_time_to_pr_minutes": avg_ttp,
        "avg_time_to_merge_minutes": avg_ttm,
        "generated_at": now(),
    }), 200


# ---------- Status Dashboard ----------
# Answers the engineering leader question: "How do I know this is working?"
# Shows active sessions, elapsed time, resolution rate, and links to every
# Devin session and PR. Auto-refreshes every 30s.

DASHBOARD_CSS = """
  body { font-family: -apple-system, sans-serif; margin: 0; background: #f8fafc; color: #1a1a1a; }
  .header { background: #483fad; color: white; padding: 20px 32px; }
  .header h1 { font-size: 20px; margin: 0; }
  .header p { font-size: 13px; opacity: 0.8; margin: 4px 0 0; }
  .stats { display: flex; gap: 16px; padding: 20px 32px; flex-wrap: wrap; }
  .stat { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 20px; min-width: 110px; }
  .stat .num { font-size: 26px; font-weight: 700; }
  .stat .label { font-size: 11px; color: #64748b; margin-top: 2px; }
  .stat.working .num { color: #d97706; }
  .stat.ready .num { color: #16a34a; }
  .stat.merged .num { color: #483fad; }
  .stat.error .num { color: #dc2626; }
  .stat.throughput .num { color: #0891b2; }
  .stat.time .num { font-size: 20px; color: #475569; }
  table { width: calc(100% - 64px); margin: 0 32px 32px; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
  th { background: #483fad; color: white; text-align: left; padding: 10px 14px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
  td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; font-size: 13px; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f8fafc; }
  a { color: #483fad; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .metrics-link { font-size: 11px; color: #94a3b8; padding: 0 32px 4px; }
  .refresh { font-size: 11px; color: #94a3b8; padding: 0 32px 16px; }
"""

@app.route("/status", methods=["GET"])
def status():
    rows = ""
    for s in sorted(sessions.values(), key=lambda x: x["issue_number"], reverse=True):
        age = elapsed(s["started_at"])
        status_badge = {
            "working":  f"🟡 Working · {age}",
            "pr_ready": f"🟢 PR Ready · {age}",
            "merged":   f"✅ Merged · {age}",
        }.get(s["status"], f"❌ Error · {age}")
        session_cell = "❌ No session" if s["status"] == "error" else f'<a href="{s["session_url"]}">Session</a>'
        pr_cell = f'<a href="{s["pr_url"]}">#{s["pr_number"]}</a>' if s.get("pr_url") else "—"
        ttp = f'{s["time_to_pr_minutes"]} min' if s.get("time_to_pr_minutes") else "—"
        rows += f"""
        <tr>
          <td><a href="{s['issue_url']}">#{s['issue_number']}</a></td>
          <td>{s['issue_title']}</td><td>{status_badge}</td>
          <td>{session_cell}</td><td>{pr_cell}</td>
          <td>{ttp}</td><td>{s['started_at']}</td>
        </tr>"""

    total = len(sessions)
    working = sum(1 for s in sessions.values() if s["status"] == "working")
    pr_ready = sum(1 for s in sessions.values() if s["status"] == "pr_ready")
    merged = sum(1 for s in sessions.values() if s["status"] == "merged")
    errors = sum(1 for s in sessions.values() if s["status"] == "error")
    resolved = pr_ready + merged
    resolved_pct = f"{int(resolved / total * 100)}%" if total > 0 else "—"
    ttp_values = [s["time_to_pr_minutes"] for s in sessions.values() if s.get("time_to_pr_minutes")]
    avg_ttp = f"{round(sum(ttp_values)/len(ttp_values))} min" if ttp_values else "—"
    empty_row = '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:32px;">No sessions yet — create a GitHub issue to trigger the automation.</td></tr>'

    return f"""<!DOCTYPE html><html><head>
  <title>Devin Automation — Status Dashboard</title>
  <meta http-equiv="refresh" content="30">
  <style>{DASHBOARD_CSS}</style></head><body>
  <div class="header"><h1>🤖 Devin Automation — Status Dashboard</h1>
  <p>Event-driven remediation · {GITHUB_REPO} · Auto-refreshes every 30s</p></div>
  <div class="stats">
    <div class="stat"><div class="num">{total}</div><div class="label">Total Sessions</div></div>
    <div class="stat working"><div class="num">{working}</div><div class="label">In Progress</div></div>
    <div class="stat ready"><div class="num">{pr_ready}</div><div class="label">PR Ready</div></div>
    <div class="stat merged"><div class="num">{merged}</div><div class="label">Merged</div></div>
    <div class="stat error"><div class="num">{errors}</div><div class="label">Errors</div></div>
    <div class="stat throughput"><div class="num">{resolved_pct}</div><div class="label">Resolution Rate</div></div>
    <div class="stat time"><div class="num">{avg_ttp}</div><div class="label">Avg Time to PR</div></div>
  </div>
  <table><tr><th>Issue</th><th>Title</th><th>Status</th><th>Devin Session</th><th>Pull Request</th><th>Time to PR</th><th>Started</th></tr>
    {rows or empty_row}
  </table>
  <div class="metrics-link">Machine-readable metrics: <a href="/metrics">/metrics</a></div>
  <div class="refresh">Page auto-refreshes every 30 seconds.</div>
</body></html>"""


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "sessions": len(sessions)}), 200


if __name__ == "__main__":
    if not DEVIN_API_KEY:
        print("ERROR: DEVIN_API_KEY environment variable is not set.")
        exit(1)
    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not set — issue comments will be skipped.")
    print(f"[+] Loaded {len(sessions)} sessions from {STATE_FILE}")
    print("[+] Webhook server starting on port 3000...")
    print("[+] Status dashboard:  http://localhost:3000/status")
    print("[+] Metrics endpoint:  http://localhost:3000/metrics")
    app.run(port=3000, debug=True)
