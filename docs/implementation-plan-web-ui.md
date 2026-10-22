# Plan: local WhatsApp-style web UI (with a "behind the scenes" console tab)

## Context
Manual testing showed the agent works well in the terminal, but a terminal doesn't give testers the feel of talking to a store on WhatsApp. The user wants a web UI that testers run **locally**, with **two tabs in the page**:
- **Chat:** a WhatsApp-style conversation, the customer experience.
- **Console:** a terminal-style "behind the scenes" view of the same conversation, showing the tool calls, the data returned, tokens and cost.

Decided by the user:
- Local only, so no new public surface; the proxy on Render is unchanged.
- **Real WhatsApp integration is not built**, only documented as future work.

The briefing allows "CLI, notebook, API ou UI simples", so the web UI adds to the CLI and doesn't replace it.

## Design: reuse everything, add one thin layer
```
browser (localhost) ──► emporio/web.py (FastAPI) ──► Agent (emporio/agent.py, unchanged)
   static/index.html         /api/session, /api/chat        └─ tools, data, prompt (unchanged)
   (no external libs)        in-memory sessions             └─ client: direct OR proxy (llm.make_client)
```
- **No changes to the agent, tools, prompt or proxy.** `web.py` creates the same `Agent` the CLI uses, so direct and proxy modes both work (the proxy mode is the reviewers' default), and replies are identical to the CLI's.
- **Run it:** `python -m emporio.web [--mode proxy|direct] [--now ISO] [--port 8000]`. It starts on `127.0.0.1` only and opens the browser automatically.
- **New runtime dependencies:** `fastapi` and `uvicorn` move into `requirements.txt`. They're already pinned for the proxy, and reviewers install a single requirements file.
- The `Turn` object already carries `tool_calls`, `tokens`, `cost_usd`, `api_calls` and `model`, so the console tab needs no new agent code.

### Endpoints (`emporio/web.py`, about 120 lines, `create_app(agent_factory)` for testing)
| Endpoint | What it does |
|---|---|
| `GET /` | Serves `emporio/static/index.html`, with a per-launch random page token injected |
| `POST /api/session` | Starts a new conversation: `{session_id, mode, model, simulated_now}` |
| `POST /api/chat` `{session_id, message}` | `agent.send()` in a worker thread: `{reply, tool_calls[], tokens, cost_usd, session_cost_usd, model}` |
| `GET /api/history?session_id=` | The conversation so far, so a page refresh doesn't lose it |

**Local safety:**
- Bound to `127.0.0.1`, so nothing is reachable from the network.
- Every POST requires the page token as a header, and the body must be JSON. A malicious website open in the same browser therefore can't make the local server spend API credits: the browser blocks it from reading the token, and from sending JSON cross-origin without permission.
- At most 20 sessions in memory.
- The agent's existing limits still apply: input length, tool rounds, 50 turns or US$0.50 per session.
- API errors return the same friendly pt-BR messages as the CLI (`api_error_message`, moved from `cli.py` into a shared module).

### Page (`emporio/static/index.html`, one self-contained file, no CDN or framework)
- **Tab "💬 Chat" (pt-BR, WhatsApp look):**
  - A green header with a store avatar, "Empório da Música" and the status "online" / "digitando…".
  - The beige WhatsApp background.
  - Customer bubbles on the right (light green), assistant bubbles on the left (white), with times and ✓✓ ticks.
  - A typing indicator while waiting; the input box and send button; Enter sends.
  - **Clickable suggestion chips** taken from the README's "Things to try", e.g. "Violões até R$ 1000", "Takamine GD20", "Status do pedido 8", "WhatsApp da loja". Non-technical testers can start with one click.
  - A tiny, safe Markdown renderer: HTML is escaped first, then **bold**, bullet lists and line breaks are applied, so no injection is possible.
- **Tab "🖥️ Console" (English, technical, dark terminal style):** for each turn, the customer message, then each tool call (name, input JSON, collapsible output JSON), then calls/tokens/cache/cost and the model. The session total sits at the top. It's the `--debug` view, in the browser.
- **Top bar:** the mode (proxy/direct), the simulated date if `--now` was used, and a "Nova conversa" button.
- A first-load notice in proxy mode: "conectando ao servidor (até 1 min)".

## Files
| File | Change |
|---|---|
| `emporio/web.py` (new) | FastAPI app, sessions, page token, browser auto-open |
| `emporio/static/index.html` (new) | Chat and console tabs; HTML, CSS and JS in one file |
| `emporio/messages.py` (new, tiny) | `api_error_message()`, shared by the CLI and the web UI |
| `emporio/cli.py` | Imports `api_error_message` from the shared module |
| `requirements.txt` | + `fastapi`, `uvicorn` (same pins as the proxy) |
| `tests/test_web.py` (new) | TestClient with a fake model client: page and token, chat round trip with tool calls, missing/wrong token → 403, unknown session → 404, history, API error → friendly message. No network, no cost |
| `scripts/build_pdf.py` | Image links become local file URIs, so screenshots render in the PDF |
| `README.md` | Quick start option **C. Web chat**; two real screenshots (`docs/img/`); WhatsApp integration design under future work |
| `docs/decision-log.md` | D26 (local web UI with two tabs), D27 (real WhatsApp documented, not built) |
| `CHANGELOG.md`, `CLAUDE.md` | Synced |

**Screenshots:** I start the local server, hold a short real conversation through `/api/chat` (about US$0.002), then capture both tabs with headless Chrome via `?session=…&tab=…`. Real data, not mock-ups.

**WhatsApp future-work design (README text only):**
- WhatsApp Cloud API (Meta) or a Twilio webhook, as `POST /webhook` on the Render service.
- The webhook verifies the request signature, maps each phone number to a session, runs the same `Agent` server-side, and sends the reply through the API.
- Needs a Meta Business account, a verified number and message templates for business-initiated messages. Phone numbers are personal data (LGPD), so they get minimal retention.
- Effort is estimated at 2–4 h plus account approval.

## Stages and commits (standing permission: commit and push when tests pass and the scan is clean)
1. `messages.py` refactor, `web.py`, `index.html`, `test_web.py`, `requirements.txt` → pytest green, plus a manual smoke run → commit.
2. Screenshots, README option C, future-work text, D26/D27, CHANGELOG, PDF image fix → commit.

Estimate: about 2–2.5 h. Then the final steps carry on as planned: release 1.0.0, the final PDF with the access page, and a security sweep.

## Verification
- `pytest`: all existing tests plus the new web tests pass.
- **Manual, direct mode:** `python -m emporio.web --mode direct` → the browser opens. Then:
  - a suggestion chip gives a correct answer in a bubble;
  - the console tab shows the tool calls and cost;
  - a refresh keeps the conversation;
  - "Nova conversa" resets it.
- **Manual, proxy mode:** `python -m emporio.web --mode proxy` gives the same behaviour through Render.
- A `curl` POST without the page token returns 403.
- The PDF renders the screenshots; the links check passes; the gated commit's secret scan is clean.
- Spend reported (expected under US$0.01).
