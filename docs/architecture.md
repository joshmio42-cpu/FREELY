# MVP architecture

```text
Remote OK public API + permission-gated Freelancer.com official API
  -> deterministic Scout
  -> PostgreSQL raw + normalized records
  -> deterministic pre-filter
  -> Fit Agent (score and fatal-risk gate)
  -> Research/Solution Agent (feasibility gate)
  -> Proposal Agent (approved claims only)
  -> Critic Agent (truthfulness and quality gate)
  -> Telegram draft
  -> human review and manual submission
```

n8n owns scheduling and delivery. The FastAPI service owns source normalization, agent contracts,
validation, database writes, and message rendering. Each agent can be called independently.

## Deliberate exclusions

- No marketplace scraping or browser automation
- No automatic submission
- No Qdrant, RAG, or long-term memory in the MVP
- No CrewAI, LangGraph, AG2, or duplicate workflow engine
- No proposal self-modification from outcomes
- No dashboard until Telegram review has been validated in real use

Freelancer.com discovery is off by default. Enabling it requires both an OAuth token and an
operator attestation that express written API permission has been obtained. It joins the same
deterministic filter and human-gated proposal path; it does not introduce a bidding capability.
