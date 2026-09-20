# FREELY

FREELY is a human-gated freelance opportunity acquisition system. It discovers permitted
opportunity feeds, evaluates realistic fit, designs a delivery approach, drafts a proposal,
critically reviews it, and sends the result to Telegram. It never submits an application or bid.

## MVP scope

- Remote OK, Jobicy, and Remotive public APIs
- GitHub public issue search restricted to explicit paid-task and bounty signals
- Freelancer.com official job-alert email intake
- Permission-gated Freelancer.com official API project search
- Deterministic sanitization, normalization, deduplication, and pre-filtering
- Fit, research/solution, proposal, and critic agents with typed outputs
- PostgreSQL audit trail and status history
- n8n scheduling and Telegram delivery
- Manual submission and manual outcome tracking

### Opportunity reach

The fit system favors small, well-bounded jobs that can build early reviews without overstating
experience. Supported reach includes data entry and cleanup, spreadsheet work, public-source
research, virtual assistance, AI-assisted content and document formatting, resume formatting,
public-page scraping, n8n/Make/Zapier workflows, API and chatbot setup, Google Sheets automation,
lead and recruitment pipelines, prompt workflows, document extraction, simple website setup,
basic Python utilities, and automation troubleshooting.

This wider discovery scope does not make every matching job proposal-ready. The deterministic
safety filter still rejects scam and abuse signals, and the Fit Agent still requires realistic
deliverability. Clarification needs and bridgeable skill gaps may proceed to a proposal rather
than being automatically rejected. Broad AI-engineer roles,
senior-development contracts, large SaaS or mobile builds, access-control bypass, spam, fake
engagement, and unsupported specialist work remain outside the automatic proposal path.

Marketplace scraping, autonomous submission, vector databases, long-term
agent memory, and dashboards are intentionally excluded.

Jobicy and Remotive listings retain their source links and attribution. GitHub issues are treated
as leads only: compensation must be verified manually before responding, and FREELY never posts a
comment or opens a pull request. A GitHub token is optional and only raises the public API rate
limit; unauthenticated discovery remains the default.

To control AI spend and keep the results useful, each command processes at most
`PIPELINE_PROCESS_LIMIT` queued Freelancer alerts (5 by default). Leads are labeled **Strong** at
70 or above and **Possible** below 70. Both receive proposals unless the work is unsafe, deceptive,
or realistically undeliverable. Previously finalized items are not processed again.

## Telegram command

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`, then restart the API. The API polls
Telegram directly, so it works on localhost without a public webhook. Only the configured chat can
start a run.

Send `/go` or `/run freely` to the bot. Both commands perform the same focused run. The bot
immediately confirms that the run is active, ignores duplicate requests while one is running,
processes up to five Freelancer alerts that n8n has queued, sends every usable lead with its exact
link and proposal, and finishes with evaluation, proposal, skip, manual-review, and error counts.
It never submits a bid. The broader public-feed adapters remain in the codebase but are not run by
these commands, so they cannot bury Freelancer gigs in unrelated listings.

## Quick start

1. Copy `.env.example` to `.env` and replace every placeholder secret.
2. Add an OpenAI API key. Without it, Scout still works but agent processing is disabled.
3. Run `docker compose up --build`.
4. Open n8n at <http://localhost:5679> and create the local owner account on first launch.
5. Import `n8n/workflows/freely-mvp.json`.
6. In `Run FREELY pipeline`, create a Header Auth credential named `FREELY Internal API`
   with header `X-Internal-Token` and the value from `.env`.
7. In `Send Telegram draft`, configure the Telegram credential and replace
   `CONFIGURE_CHAT_ID` with the target chat ID.

### Freelancer.com setup

The practical default is Freelancer's own saved-search/job-alert emails. This avoids crawling the
marketplace while still giving FREELY new listings automatically:

1. On Freelancer.com, save a project search and enable its email alerts.
2. Import `n8n/workflows/freelancer-alerts.json`.
3. In `Freelancer alert email`, create an IMAP credential for the mailbox receiving those alerts.
4. In `Send alert to FREELY`, select the existing `FREELY Internal API` Header Auth credential.
5. Test with a real alert, verify the exact project link in Telegram, then activate the workflow.

FREELY parses only `https://www.freelancer.com/projects/...` links. n8n stores new alerts without
running AI or sending Telegram messages. They are evaluated only when you send `/go`. If an email
does not contain enough detail, the `/go` result includes the exact link and a details-needed notice;
the system never invents the missing brief.

The separate Freelancer API integration remains disabled by default. The Freelancer User Agreement
says automated access, including API access, requires express written permission. After obtaining
that permission, create an OAuth application/token through the developer portal, then set:

```env
FREELANCER_API_AUTHORIZED=true
FREELANCER_OAUTH_TOKEN=your-token
```

The integration searches active projects through the official API. It does not scrape pages,
place bids, send messages, or submit proposals. The normal Telegram/manual-review gate remains in
force. API data handling and retention must follow the permission and API terms granted to you.

API documentation is available at <http://localhost:8000/docs>.

## Secrets and privacy

- Copy `.env.example` to `.env`; never edit the example with real values.
- `.env`, private keys, credential exports, local databases, caches, and logs are ignored by Git.
- Configure n8n credentials inside your own n8n instance after importing a workflow. The bundled
  workflow files contain placeholders, not credential IDs or secrets.
- Never paste API keys, bot tokens, OAuth tokens, passwords, chat IDs, email addresses, or exported
  production data into an issue, pull request, screenshot, fixture, or log.
- Proposal generation sends normalized opportunity text to the configured AI provider. Review that
  provider's privacy and retention settings before processing sensitive or personal information.
- If a secret is committed, revoke and rotate it immediately. Removing it from the latest commit is
  not sufficient because it remains in Git history.

See [SECURITY.md](SECURITY.md) for private vulnerability reporting and incident guidance.
Follow the [safe publishing checklist](docs/publishing.md) before pushing this repository.

## Development

Install development dependencies and run the checks:

```bash
python -m pip install -e ".[dev]"
pytest
ruff check app tests
```

Contributions should follow [CONTRIBUTING.md](CONTRIBUTING.md).

Runtime dependencies are resolved in `requirements.lock` with SHA-256 hashes. Regenerate that file
with `pip-compile --generate-hashes pyproject.toml --output-file requirements.lock` after reviewing
dependency changes; do not hand-edit hashes.

## License

Licensed under the [MIT License](LICENSE). Third-party acknowledgements are recorded in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Safety boundary

The system has no endpoint, credential, or workflow capable of submitting marketplace bids.
Telegram actions may record statuses such as `SUBMITTED`, but only after the user has manually
submitted on the source platform.

## Attribution

The source-adapter and test-fixture design was informed by the Apache-2.0 licensed
`MSKazemi/opportunity-engine` project. Proposal qualification and writing rubrics were informed
by the MIT-licensed `abullaisi/upwork-skills` project. No browser automation or stealth scraping
code is included. Freelancer.com API paths and OAuth conventions were checked against its official
LGPL-3.0 Python SDK; the SDK is not bundled. See `THIRD_PARTY_NOTICES.md`.
