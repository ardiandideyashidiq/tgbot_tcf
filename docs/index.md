# TCF Bot Documentation Hub

This page is the entry point for repository-specific docs.
Before editing code or docs, consult the agent guidance under `agents/`, especially the workflow and style rules.
- `agents/RULES.md` - coding conventions, what is forbidden
- `agents/STYLE-CODE.md` - code style, typing, and formatting rules
- `agents/STYLE-COMMENTS.md` - comment and docstring style
- `agents/WORKFLOW.md` - branching, commit conventions, and deployment checklist
- `agents/CLAUDE.md` - project-specific guidance and gotchas
- `agents/REPLIT.md` - Replit environment, config, and secrets guidance

This documentation set is specific to the TCF bot repository. It is built from the source code in:
- `tcbot/`
- `tests/`
- `agents/`

It does not describe GitHub Actions workflows under `.github/`. For code behavior and architecture, prefer the files in this directory.

## Navigation

- [Project architecture](architecture.md)
- [Modules and service boundaries](modules.md)
- [Conversation flows and workflows](workflows.md)
- [Development workflow and onboarding](development.md)
- [AI / agent guidelines](agent-guidelines.md)

## Agent documentation references

- [Agent instructions for Claude](../agents/CLAUDE.md)
- [Replit environment notes](../agents/REPLIT.md)
- [Code style guidelines](../agents/STYLE-CODE.md)
- [Comment style guidelines](../agents/STYLE-COMMENTS.md)
- [Workflow expectations](../agents/WORKFLOW.md)
- [Project rules and constraints](../agents/RULES.md)

## Scope

This documentation focuses on the bot code and the repository conventions that matter for development and review.
It includes:

- bot startup and runtime flow
- module discovery and handler registration
- async MongoDB database helpers
- Telegram command and workflow conventions
- configuration through `config.env`
- test coverage and local verification
- agent guidance specific to this repository

## Related resources

- [README](../README.md) for quick start and project overview
- [Project architecture](architecture.md)
- [Modules and service boundaries](modules.md)
- [Conversation flows and workflows](workflows.md)
- [Development workflow and onboarding](development.md)
- [AI / agent guidelines](agent-guidelines.md)
- [Agent instructions for Claude](../agents/CLAUDE.md)
- [Replit environment notes](../agents/REPLIT.md)
- [Code style guidelines](../agents/STYLE-CODE.md)
- [Comment style guidelines](../agents/STYLE-COMMENTS.md)
- [Workflow expectations](../agents/WORKFLOW.md)
- [Project rules and constraints](../agents/RULES.md)
