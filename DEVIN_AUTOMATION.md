# Devin Automation — Event-Driven Security Remediation

Automatically remediates GitHub issues using the Devin API. When an issue is opened, a Devin session starts, investigates the problem, and opens a pull request with the fix — no human intervention required until PR review.

## How It Works

```
GitHub Issue Opened
      ↓
Webhook fires → webhook_server.py receives POST
      ↓
Calls Devin API → session starts
      ↓
🤖 Comment posted on issue: "Devin session started"
      ↓
Devin opens Pull Request
      ↓
🟢 Comment posted on issue: "PR ready for review"
      ↓
Engineer reviews and merges
```

## Files

| File | Purpose |
|---|---|
| `webhook_server.py` | Flask server — receives GitHub webhooks, calls Devin API, posts status comments |
| `Dockerfile.webhook` | Packages the server into a container |
| `docker-compose.webhook.yml` | One-command startup with environment variable passthrough |
| `requirements.webhook.txt` | Python dependencies (Flask, requests) |
| `sessions.json` | Auto-created — persists session state across restarts |

## Quick Start

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [ngrok](https://ngrok.com) account (free) — exposes your local server to GitHub
- Devin API key from [app.devin.ai](https://app.devin.ai) → Settings → API
- GitHub Personal Access Token with `repo` scope

### 1. Set environment variables
```bash
export DEVIN_API_KEY="apk_user_..."
export GITHUB_TOKEN="ghp_..."
```

### 2. Start the webhook server
```bash
docker compose -f docker-compose.webhook.yml up --build
```

Server starts on port 3000. View the status dashboard at: http://localhost:3000/status

### 3. Expose it to the internet
```bash
ngrok http 3000
```

Copy the `https://....ngrok-free.dev` URL.

### 4. Add GitHub webhook
Go to **github.com/lochenger/superset/settings/hooks/new**:
- **Payload URL:** `https://your-ngrok-url.ngrok-free.dev/webhook`
- **Content type:** `application/json`
- **Secret:** `superset-webhook-secret`
- **Events:** Issues + Pull requests

### 5. Test it
Create a new issue in this repo. Within seconds:
- A 🤖 comment appears on the issue with the Devin session link
- The dashboard at `/status` shows the session as 🟡 Working
- When Devin opens a PR, the status flips to 🟢 PR Ready

## Status Dashboard

Visit `/status` for a live view of all sessions:

| Column | Meaning |
|---|---|
| Issue | GitHub issue that triggered the session |
| Status | 🟡 Working · 🟢 PR Ready · ❌ Error — with elapsed time |
| Devin Session | Link to the live Devin session |
| Pull Request | Link to the PR Devin opened |
| Resolution Rate | % of sessions that produced a PR |

## Observability Endpoints

| Endpoint | Description |
|---|---|
| `GET /status` | Live HTML dashboard |
| `GET /health` | JSON health check with session count |
| `POST /webhook` | GitHub webhook receiver |

## Issues Remediated

| Issue | Package | CVE | PR |
|---|---|---|---|
| #1 | flask 2.3.3 | GHSA-68rp-wp8r-4726 | #14 |
| #2 | paramiko 3.5.1 | GHSA-r374-rxx8-8654 | — |
| #3 | @sigstore/core ≤3.2.0 | GHSA-jfc7-64v2-mr8c | — |
| #4 | js-yaml ≤4.1.1 | GHSA-h67p-54hq-rp68 | — |
| #9 | Pillow | CVE-2026-40192 | #10 |
| #11 | cryptography 48.0.1 | AIKIDO-2026-94131 | #12 |
