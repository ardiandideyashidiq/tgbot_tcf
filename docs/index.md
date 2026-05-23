# TCF Bot — Documentation Hub

This is the entry point for all project documentation. Start here and follow the links to the section most relevant to your task.

Before editing code or documentation, review the agent guidance in `agents/` first.

---

## Agent Instructions (AI agents — read these first)

| File | Purpose |
|---|---|
| [agents/CLAUDE.md](../agents/CLAUDE.md) | Primary agent reference: architecture, role system, conventions, what not to do |
| [agents/RULES.md](../agents/RULES.md) | Hard project rules and constraints |
| [agents/STYLE-CODE.md](../agents/STYLE-CODE.md) | Code style, typing, naming, alignment, decorator stack |
| [agents/STYLE-COMMENTS.md](../agents/STYLE-COMMENTS.md) | Comment and docstring conventions |
| [agents/WORKFLOW.md](../agents/WORKFLOW.md) | Branching, commit messages, deployment checklist |
| [agents/REPLIT.md](../agents/REPLIT.md) | Replit environment, secrets, workflow, ports |

---

## Developer Documentation (human engineers)

| File | Purpose |
|---|---|
| [docs/architecture.md](architecture.md) | Startup flow, DB schema, caching, fan-out, error handling |
| [docs/modules.md](modules.md) | Per-module responsibilities and service boundaries |
| [docs/workflows.md](workflows.md) | ConversationHandler flows in full detail |
| [docs/development.md](development.md) | Setup, onboarding, adding modules and collections |

---

## Project State

| File | Purpose |
|---|---|
| [PLAN.md](../PLAN.md) | Current bugs, improvement strategy, session tracker |
| [README.md](../README.md) | Project overview, quick start, configuration reference |
| [config.env.example](../config.env.example) | Template for all required environment variables |

---

## Quick Reference

### Start the bot
```bash
python3 -m tcbot
```

### Run tests
```bash
python3 -m pytest tests/ -v
```

### Key patterns
- Role resolution: `roles_db.get_effective_role(user_id)` — cached 60 s
- Multi-group action: `fan_out([coros])` — bounded at 10 concurrent
- Decorator stack: `ratelimiter → auth_guard → log_execution` (outermost → innermost)
- ConversationHandlers: all live in `*_flow.py` — no `*_conv.py` files

### Key collections
| Collection | Purpose |
|---|---|
| `bans` | Active and historical federation bans |
| `tc_owners` | Founder (single document) |
| `tc_admins` | Admin list |
| `tc_roles` | Developer and Tester roles |
| `federated_groups` | Connected groups |
| `pending_joins` | Groups awaiting approval |
| `member_cache` | User profile snapshots |
