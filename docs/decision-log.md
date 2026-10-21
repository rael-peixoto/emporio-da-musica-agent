# Decision log

This is a dated record of the decisions behind this project: what was decided, what else was
considered, what each choice costs, and who made the call.

**How the work was done:** Rael owns every decision. Claude Code (an AI coding assistant) did
the research, proposed options and implemented the approved ones. "Decided by" names who made
each call; "proposed by Claude Code" means the option came from the assistant and Rael approved
it.

| # | Date | Decision | Decided by |
|---|---|---|---|
| [D1](#d1) | 2026-10-21 | Submit through both channels: public repo and PDF | Rael |
| [D2](#d2) | 2026-10-21 | Docs in English, agent in Brazilian Portuguese | Rael (proposed by Claude Code) |
| [D3](#d3) | 2026-10-21 | Isolated repository; case data kept byte-identical | Rael (proposed by Claude Code) |
| [D4](#d4) | 2026-10-21 | Approval-gated AI workflow; `CLAUDE.md` published | Rael |
| [D5](#d5) | 2026-10-21 | Function calling over deterministic Python tools | Rael (proposed by Claude Code) |
| [D6](#d6) | 2026-10-21 | Full policy manual in the system prompt (no RAG) | Rael |
| [D7](#d7) | 2026-10-21 | Command-line interface | Rael |
| [D8](#d8) | 2026-10-21 | "Today" = real clock, with a `--now` override | Rael |
| [D9](#d9) | 2026-10-21 | Claude Haiku 5.5 by default; Sonnet 5.5 only if evals require it | Rael (options researched by Claude Code) |
| [D10](#d10) | 2026-10-21 | Plain SDK with a hand-written tool loop | Rael (proposed by Claude Code) |
| [D11](#d11) | 2026-10-21 | Conversation history kept only for one session | Rael (proposed by Claude Code) |
| [D12](#d12) | 2026-10-21 | Explicit handling for each data/policy inconsistency | Rael (proposed by Claude Code) |
| [D13](#d13) | 2026-10-21 | Prepaid API budget with auto-reload off | Rael |
| [D14](#d14) | 2026-10-21 | Hosted proxy for reviewers, plus direct mode | Rael |
| [D15](#d15) | 2026-10-21 | Layered cost and abuse safeguards | Rael (designed with Claude Code) |
| [D16](#d16) | 2026-10-21 | Pinned dependency versions | Rael (proposed by Claude Code) |
| [D17](#d17) | 2026-10-21 | Spend limit on the existing workspace (no dedicated one) | Rael |
| [D18](#d18) | 2026-10-21 | Standing permission for stage commits | Rael |
| [D19](#d19) | 2026-10-21 | Fixes from the first live run | Rael (found by Claude Code) |
| [D20](#d20) | 2026-10-21 | Keep Claude Haiku 5.5 after the evaluations | Rael (rule set in D9) |
| [D21](#d21) | 2026-10-21 | Enforce pt-BR replies in code, not only in the prompt | Rael (measured by Claude Code) |
| [D22](#d22) | 2026-10-21 | Prompt fixes from reviewing the example transcripts | Rael (found by Claude Code) |
| [D23](#d23) | 2026-10-21 | pt-BR by default; English answers allowed (supersedes D21) | Rael |
| [D24](#d24) | 2026-10-21 | No Sonnet comparison run; Haiku is enough at this scale | Rael |
| [D25](#d25) | 2026-10-21 | WhatsApp number from §7 (revises D12, item 5) | Rael |
| [D26](#d26) | 2026-10-21 | Local WhatsApp-style web chat with a console tab (extends D7) | Rael |
| [D27](#d27) | 2026-10-21 | Real WhatsApp integration documented, not built | Rael |

---

<a id="d1"></a>
### D1 · Submit through both channels: public repo and PDF
- **Context:** The case briefing asks for a public GitHub repository link in reply to the
  e-mail. The recruiter's e-mail asks for a PDF uploaded to a form, with all responses in
  English.
- **Options:** repo link only · PDF only · both.
- **Decision:** both. The public repo holds every deliverable. The PDF is generated from the
  README and documentation and named as the e-mail requests.
- **Trade-offs:** a small amount of extra work (a PDF build script). In return, neither
  channel's requirements are missed, and the PDF can never drift from the repo.
- **Decided by:** Rael.

<a id="d2"></a>
### D2 · Docs in English, agent in Brazilian Portuguese
- **Context:** the briefing is in Portuguese, the recruiter asks for English, and the store's
  customers speak Portuguese.
- **Decision:**
  - Code, comments, commit messages and documentation are in English.
  - Everything the customer sees is in Brazilian Portuguese (pt-BR), including the system
    prompt and the example conversations (which are real transcripts).
- **Trade-offs:** the repository mixes two languages, but each audience reads its own.
- **Decided by:** Rael (proposed by Claude Code).

<a id="d3"></a>
### D3 · Isolated repository; case data kept byte-identical
- **Context:** the local working folder also held the recruiter's e-mail, which contains
  personal data and an application link.
- **Options:**
  - Make the working folder the repo and git-ignore the e-mail (one careless `git add .` away
    from a leak).
  - Use a dedicated subfolder as the repo.
- **Decision:**
  - A dedicated repository folder. The case data was copied into it, and file hashes confirmed
    the copies are identical.
  - `.gitattributes` turns off line-ending conversion for `data/`, so every clone, on any
    operating system, gets exactly the files Artefact provided.
  - Raw data is read-only; all cleaning happens in code.
- **Trade-offs:** a duplicate copy of the data on the author's disk, in exchange for no
  accidental leak and full fidelity to the source.
- **Decided by:** Rael (proposed by Claude Code).

<a id="d4"></a>
### D4 · Approval-gated AI workflow; `CLAUDE.md` published
- **Context:** the briefing evaluates how AI coding assistants are used.
- **Decision:**
  - Claude Code works under the rules in [`CLAUDE.md`](../CLAUDE.md), following the workflow
    understand → research → plan → execute → test → document.
  - Rael approves every plan and every commit.
  - The assistant separates facts from assumptions, never claims a test passed without
    showing the output, and never invents data or policy rules.
  - `CLAUDE.md` is committed so the workflow is visible.
- **Trade-offs:** slower than letting the assistant run freely, but every decision has an
  owner and a record (this file).
- **Decided by:** Rael.

<a id="d5"></a>
### D5 · Function calling over deterministic Python tools
- **Context:** the agent has to know when to query live data (products, stock, prices,
  promotions, orders) and must never get a number wrong. The policy manual itself forbids
  quoting prices, stock or delivery times without checking the system.
- **Options:**
  - RAG (retrieval over embeddings) of the CSV rows. Poor at numeric filters such as "up to
    R$ 1,000".
  - A text-to-SQL agent. Flexible, but the model could reach the customers table (personal
    data), and pricing rules would be hard to guarantee.
  - Function calling with purpose-built tools.
  - Agent frameworks (LangChain, LlamaIndex).
- **Decision:**
  - Function calling. The model decides *when* to call a tool; Python does the lookup and all
    arithmetic (promo price, PIX price, maximum installments, day counts).
  - Customer data is reachable only through an order lookup that requires the order number
    plus a matching e-mail or phone.
- **Trade-offs:** less flexible for questions no tool anticipates (the agent says it can't
  check that and offers a human). In return: exact numbers, a privacy boundary enforced in
  code, and logic that can be tested without calling a model.
- **Decided by:** Rael (proposed by Claude Code).

<a id="d6"></a>
### D6 · Full policy manual in the system prompt (no RAG)
- **Context:** the manual is 8 pages (about 5–6k tokens).
- **Options:**
  - The whole manual in the prompt.
  - A tool that returns a manual section on request.
  - Embedding-based RAG.
- **Decision:** the full manual (a reviewed Markdown transcription) goes in the system prompt,
  and prompt caching keeps it cheap.
- **Trade-offs:**
  - Policy look-ups don't appear as separate tool calls.
  - The approach would not scale to a manual hundreds of pages long; then a retrieval step
    would be added.
  - In return, there are no retrieval misses, rules that span sections are always together
    (for example, the 5% PIX discount never stacks on a promotional price), and it's the least
    code.
  - Cached input costs one-tenth of the normal input price on Haiku 5.5.
- **Decided by:** Rael.

<a id="d7"></a>
### D7 · Command-line interface
- **Options:** command line only · command line plus a Streamlit web UI · Streamlit only.
- **Decision:** a command-line chat.
  - `--debug` prints every tool call.
  - `--save` writes the conversation, including tool calls, to Markdown.
- **Trade-offs:** a less polished demo, but it's the fastest to build and run. `--save` also
  guarantees the example conversations are real transcripts, not hand-written ones.
- **Decided by:** Rael.

<a id="d8"></a>
### D8 · "Today" = real clock, with a `--now` override
- **Context:** the order data ends in March 2026. Against the real date (October 2026), every
  return window has expired and pending orders look stale.
- **Options:** real clock only · a fixed simulated date · real clock with an override.
- **Decision:** the real clock in Campo Grande time (America/Campo_Grande) by default.
  `--now 2026-03-25T10:00` simulates another moment for demos and tests, and each example
  states the date it used.
- **Trade-offs:** the default is honest; showing an in-window return needs an explicit flag.
- **Decided by:** Rael.

<a id="d9"></a>
### D9 · Claude Haiku 5.5 by default; Sonnet 5.5 only if evals require it
- **Research** (official pricing and deprecation pages, 2026-10-21; US$ per 1M input / output
  tokens):

  | Option | Finding |
  |---|---|
  | Claude Haiku 5.5 | US$0.10 / US$0.50; native tool use |
  | Claude Sonnet 5.5 | US$2 / US$10 |
  | Claude 3 Haiku | Retired on 2026-04-19 |
  | gpt-4o-mini | US$0.15 / US$0.60; deprecated, shutdown on 2027-01-14 |
  | gpt-6-luna (OpenAI's named successor) | US$0.10 / US$0.50 |
  | Llama 3 8B via Ollama | No tool-calling support and an 8K context window; our prompt alone is about 7–8k tokens |
  | Qwen3 / Llama 3.1 8B via Ollama | Viable, but on the development machine (3 GB GPU) they would run mostly on the CPU, and reviewers would need a ~5 GB download |

- **Decision:**
  - Use the Anthropic SDK with Claude Haiku 5.5 by default.
  - Run the same scenario suite on Sonnet 5.5, and switch only if Haiku fails a critical
    scenario.
  - No local models for now; they are listed as a future optimisation. No second provider
    SDK, since OpenAI offers no price advantage.
- **Trade-offs:** Haiku may be weaker on subtle policy questions. That risk is measured rather
  than assumed; results are in the README.
- **Decided by:** Rael (options researched by Claude Code).

<a id="d10"></a>
### D10 · Plain SDK with a hand-written tool loop
- **Options:** LangChain, LangGraph or LlamaIndex · the Anthropic SDK's beta tool runner · a
  manual loop.
- **Decision:** a manual tool loop of about 40 lines.
- **Trade-offs:** slightly more code than the tool runner. In return, nothing is hidden for a
  reviewer to decode, there is no dependency on a beta feature, and we control the history,
  the per-message limits and the transcript logging.
- **Decided by:** Rael (proposed by Claude Code).

<a id="d11"></a>
### D11 · Conversation history kept only for one session
- **Decision:** history lives in memory for one session; transcripts are written only with
  `--save`.
- **Trade-offs:** returning customers are not remembered. A command-line tool has no customer
  login, so persisting conversations would mix people's data. Not persisting follows the
  data-minimisation principle of Brazil's data-protection law (LGPD).
- **Decided by:** Rael (proposed by Claude Code).

<a id="d12"></a>
### D12 · Explicit handling for each data/policy inconsistency
- **Context:** the CSVs and the manual contradict themselves in several places.
- **Decision:**
  - Every contradiction gets one written rule, implemented in code or in the prompt.
  - The full list is in the README's [Assumptions](../README.md#7-assumptions) section.
  - The guiding principle: where a rule is ambiguous, read it in the customer's favour, as
    Brazil's Consumer Protection Code requires (CDC, art. 47).
- **Trade-offs:** some calls (for example, which phone number to give customers) can't be
  verified with the store. Each one is stated openly instead of guessed silently.
- **Decided by:** Rael (proposed by Claude Code).

<a id="d13"></a>
### D13 · Prepaid API budget with auto-reload off
- **Context:** US$5 of prepaid Anthropic credits. Enabling auto-reload would charge US$15
  upfront.
- **Decision:** prepaid only, with auto-reload off. Estimated spend is reported after every
  run that calls the model.
- **Trade-offs:** the service stops if credits run out, but the worst-case loss is capped at
  the balance.
- **Decided by:** Rael.

<a id="d14"></a>
### D14 · Hosted proxy for reviewers, plus direct mode
- **Context:** reviewers should be able to try the agent without their own API key, and
  Rael's key must never leave a server he controls.
- **Options:**
  - Reviewers bring their own key.
  - Share a limited key privately.
  - Host a web demo.
  - Keep the local command-line agent and route its model calls through a hosted proxy.
- **Decision:**
  - By default, the agent runs on the reviewer's machine and its model calls go to a small
    FastAPI proxy hosted on Render, which holds the key as a server-side environment variable.
  - Reviewers who have their own key can bypass the proxy (direct mode).
  - Both modes run the same agent code; only the API endpoint and credential differ.
- **Trade-offs:**
  - Adds a small server and a deployment step.
  - The free hosting tier sleeps when idle, so the first request can take about a minute.
  - The proxy's usage counters reset on restart; the Anthropic-side spend limit (D15) is the
    persistent backstop.
- **Decided by:** Rael.

<a id="d15"></a>
### D15 · Layered cost and abuse safeguards
- **Decision:**
  - A prepaid balance with no auto-reload.
  - A monthly spend limit on the Anthropic workspace that holds the key (see D17).
  - Secret hygiene: keys stay out of git, and GitHub push protection (which detects Anthropic
    keys) is enabled.
  - A proxy access code, compared in constant time.
  - The proxy overrides the model, the length cap, the system prompt and the tool list with its
    own copies, so it can't be used as a general-purpose Claude endpoint.
  - Request-size limits, a global rate limit and a daily dollar budget.
  - Client-side limits: tool rounds per message, input length, and spend per session.
  - Logs record usage metadata only: no message content, no IP addresses.
- **Rejected:** per-IP rate limiting. Render's `X-Forwarded-For` header can be spoofed by the
  client, so it would give false assurance.
- **Trade-offs:** reviewers need an access code (delivered with the submission, never
  published). The in-memory limits reset on restart, which the Anthropic workspace limit
  covers.
- **Decided by:** Rael (designed with Claude Code).

<a id="d16"></a>
### D16 · Pinned dependency versions
- **Decision:** exact versions in `requirements*.txt`, all verified to install on Python 3.14
  (including `anthropic==2.0.0`, a newer major version than the SDK documentation consulted;
  its API was smoke-tested before use).
- **Trade-offs:** no automatic security updates, in exchange for reviewers running exactly
  what was tested.
- **Decided by:** Rael (proposed by Claude Code).

<a id="d17"></a>
### D17 · Spend limit on the existing workspace (no dedicated one)
- **Context:** the plan proposed a dedicated Anthropic workspace for the proxy key, based on
  documentation saying the default workspace can't have limits. The Console did accept a
  US$3 monthly limit on the workspace that already held the key, so that research note was
  wrong.
- **Options:** keep one key and use it locally and on the proxy · create a second key in the
  same workspace · create a dedicated workspace.
- **Decision:** a US$3 monthly limit on the existing workspace. The same key may be used on
  the proxy; a second key in the same workspace remains optional, and would only add the
  ability to revoke the proxy independently.
- **Trade-offs:** development and reviewer usage share the same US$3 cap, so development spend
  is kept low and reported after every run.
- **Decided by:** Rael.

<a id="d18"></a>
### D18 · Standing permission for stage commits
- **Context:** with the deadline close, waiting for approval on every commit was the main
  source of delay.
- **Decision:** Claude Code may commit and push at each stage checkpoint, but only when the
  tests pass and after scanning the staged changes for secrets. It reports what went in
  afterwards. New repositories, deployments, publishing and history rewrites still need
  explicit approval each time.
- **Trade-offs:** less review before each commit, offset by small single-stage commits, a
  report after each one, and the ability to revert.
- **Decided by:** Rael.

<a id="d19"></a>
### D19 · Fixes from the first live run
- **Context:** the first live session answered the briefing's four questions with correct
  values, for US$0.0038. Reading the transcript critically turned up three problems:
  - The model worked out a return deadline itself (correctly, but by its own arithmetic).
  - It "corrected" a product name from the data ("Cedr" → "Cedro").
  - It assumed the customer's gender from her name ("contatada").
- **Decision:**
  - The order lookup now returns the policy deadlines already computed: regret return (7 days
    after delivery), defect exchange (30 days after purchase) and legal warranty (90 days
    after delivery). Each is marked "dentro do prazo" or "prazo encerrado".
  - The prompt requires product names exactly as the tools return them, and gender-neutral
    phrasing.
  - `--debug` now prints token and cache usage, which confirmed that prompt caching works:
    8,246 tokens written once, then read from cache.
- **Trade-offs:** slightly larger tool outputs, in exchange for policy answers that rest on
  computed dates rather than the model's arithmetic. Haiku follows style instructions loosely
  at low effort; the scenario evaluations check this.
- **Decided by:** Rael (found by Claude Code).

<a id="d20"></a>
### D20 · Keep Claude Haiku 5.5 after the evaluations
- **Context:** D9 set the rule: keep Haiku unless it fails a critical scenario.
- **Evidence:**
  - 21 scripted scenarios: the briefing's four questions, catalogue edge cases, scope,
    privacy and prompt injection, and service flows.
  - **21/21 passed**, at US$0.0097 for the whole suite.
  - Every transcript was read by hand, and its prices and dates checked against the data.
  - The single failure in the first run was a check that was too narrow (the reply was
    correct); the check was fixed and the suite re-run.
- **Decision:** Haiku 5.5 at effort `low` stays the default, in both direct mode and the proxy.
- **Trade-offs:** a stronger model could phrase edge cases more carefully, at about 20× the
  cost. The suite makes switching a measured decision (`--model`).
- **Decided by:** Rael (rule set in D9).

<a id="d21"></a>
### D21 · Enforce pt-BR replies in code, not only in the prompt
> **Superseded by [D23](#d23):** the requirement changed, and this mechanism was removed. Kept
> as a record of how a hard rule was measured and enforced.
- **Context:** the requirement is that the agent always answers in pt-BR. Re-running the suite
  showed Haiku sometimes answering an English question in English. Each attempt was measured
  on the `idioma` scenario:

  | Attempt | Replies in pt-BR |
  |---|---|
  | Rule in the system prompt's tone section | Failed a full-suite run |
  | Rule moved to the non-negotiable list, plus a reminder in the per-call context block | 3/5 |
  | Same, at effort `medium` | 4/5 (rejected: costs more on every call and is still unreliable) |
  | A mid-conversation `system` message after each customer message | 7/8 |
  | **The same message plus a code guard** | **10/10** (8 dedicated runs + 2 full suites) |

  A mid-conversation `system` message is the API's channel for operator instructions; customer
  text can't imitate it.
- **Decision:** keep the mid-conversation reminder, and add the code guard.
  - The guard counts English vs Portuguese function words in the final reply. If the reply
    looks English, the same request is sent once more and the English reply is discarded.
  - The discarded reply never enters the history, so the history stays append-only, as the
    API requires.
  - The proxy accepts only this exact reminder text as a `system` message.
- **Trade-offs:** an occasional extra call (about US$0.0005), and a word-count heuristic
  rather than a language model. That is enough for English vs Portuguese, not for every
  language. It follows the project's principle (D5): hard rules are enforced in code, and the
  prompt alone is not trusted with them.
- **Decided by:** Rael (measured by Claude Code).

<a id="d22"></a>
### D22 · Prompt fixes from reviewing the example transcripts
- **Context:** every example conversation was read in full, and its amounts were checked
  automatically against the data. The review found:
  - The credit-card rules were quoted from the manual's summary table ("parcela mínima de
    R$ 100,00"), contradicting the documented assumption that the §3.1 tiers prevail.
  - A return handoff promised "24 horas úteis", which the manual only defines for complaints.
  - One take mentioned the internal tooling ("a ferramenta não informou um prazo").
  - One take called the ukulele a "violino" and corrected itself.
- **Decision:**
  - The prompt now spells out the §3.1 tiers.
  - Handoffs other than complaints promise no deadline the manual doesn't define.
  - The prompt says never to talk about tools or internal instructions.
  - Affected examples were regenerated: real, unedited runs, never hand-edited. The scenario
    suite gained a `regras_de_parcelamento` check and was re-run: 22/22.
- **Trade-offs:** re-running an example is curation. To stay honest, the slips that were seen
  are recorded here and in the README's known limitations.
- **Decided by:** Rael (found by Claude Code).

<a id="d23"></a>
### D23 · pt-BR by default; English answers allowed (supersedes D21)
- **Context:** D21 enforced "always pt-BR" with a mid-conversation reminder and a code guard.
  Rael then revised the requirement: most customers write in Portuguese, so pt-BR is the
  default, and answering an English question in English is fine.
- **Decision:**
  - The prompt rule now reads: pt-BR by default; reply in the customer's language when they
    write in another one (e.g. English).
  - The reminder and the English-detection guard were removed, and the proxy again rejects
    any `system` message from the client.
  - The evaluation scenario now checks that an English question gets a correct answer.
- **Trade-offs:** less code and one fewer API call in edge cases. Replying in other languages
  besides English is an interpretation of the revised rule.
- **Decided by:** Rael.

<a id="d24"></a>
### D24 · No Sonnet comparison run; Haiku is enough at this scale
- **Context:** D9/D20 left an optional Sonnet 5.5 run (about US$0.20) for a comparison table.
- **Decision:** skip it. Haiku passed the critical scenarios, and its cost profile fits the
  store's scale. Revisit Sonnet if the business grows or the evaluations start failing;
  `python -m evals.run --model claude-sonnet-5-5` makes that a measured switch.
- **Trade-offs:** no measured Sonnet baseline in the README.
- **Decided by:** Rael.

<a id="d25"></a>
### D25 · WhatsApp number from §7 (revises D12, item 5)
- **Context:** the manual gives two WhatsApp numbers. The cover and the §1.2 table show
  "Telefone / WhatsApp (67) 3341-4444"; §7, the section about WhatsApp service, calls
  (67) 3321-4500 "o principal meio de atendimento remoto". The first plan gave customers
  3341-4444 for both, because it appears twice. Manual testing showed the agent quoting that
  number for WhatsApp.
- **Decision:** WhatsApp **(67) 3321-4500**, phone **(67) 3341-4444**. The section that
  describes the WhatsApp channel in detail is the more specific source. The README flags the
  conflict for the store to confirm.
- **Trade-offs:** one of the two sources is still wrong; the agent can't know which, so the
  conflict is documented rather than hidden.
- **Decided by:** Rael.

<a id="d26"></a>
### D26 · Local WhatsApp-style web chat with a console tab (extends D7)
- **Context:** manual testing showed a terminal doesn't give the feel of talking to a store on
  WhatsApp. Testers, possibly non-technical, should also be able to see *how* the agent
  reaches its answers.
- **Options:**
  - A hosted page (zero install, but a new public surface to secure).
  - A local page.
  - A web terminal running the real CLI in the browser.
- **Decision:** a local page (`python -m emporio.web`) with two tabs:
  - a WhatsApp-style chat;
  - a "behind the scenes" console with tool calls, data, tokens and cost.

  The page runs the same `Agent` in direct or proxy mode, so the agent code didn't change. It
  is one self-contained HTML file with no external libraries. It listens on `127.0.0.1` only,
  and a per-launch token protects its API from other websites.
- **Trade-offs:** testers still clone and install (the same steps as the CLI), but there's no
  new internet-facing surface to secure or pay for.
- **Decided by:** Rael.

<a id="d27"></a>
### D27 · Real WhatsApp integration documented, not built
- **Context:** connecting to real WhatsApp would be a bonus. The briefing accepts a CLI,
  notebook, API or simple UI.
- **Decision:** document a concrete design in the README's future work, and don't build it
  now. The design: a Cloud API webhook on the Render service, the same agent run server-side,
  and phone numbers treated as personal data.
- **Trade-offs:** no live WhatsApp demo. In exchange, no dependency on Meta or Twilio account
  approval before the deadline, and no need to register reviewers' phone numbers.
- **Decided by:** Rael.
