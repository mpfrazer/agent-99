# CLAUDE.md — AI Assistant Guide for agent-99

## Project Overview

**agent-99** is an experimental AI Agent runner. This repository is in early development; the canonical description lives in `README.md`.

---

## Repository Structure

```
agent-99/
├── docs/
│   └── plans/          # All AI-generated plans are stored here (see Workflow Rules)
├── README.md           # Project description
└── CLAUDE.md           # This file
```

As the project grows, this section should be updated to reflect new directories, source files, configuration, and test conventions.

---

## Mandatory Workflow Rules

These rules apply to every AI assistant working in this repository. They are non-negotiable and must be followed precisely.

### Rule 1 — Plan Before Acting

At the start of **every** command or task:

1. Perform a detailed review of the repository structure and any relevant code.
2. Use the findings plus the prompt details to create a **comprehensive, step-by-step plan**.
3. Write the plan to a file inside `docs/plans/`. Use a descriptive name, e.g.:
   - `docs/plans/YYYY-MM-DD-<short-description>.md`
   - Example: `docs/plans/2026-03-23-add-auth-module.md`
4. Do not begin implementation until the plan is stored.

### Rule 2 — Approval Required Before Every Step

- **Never perform any action** (file edits, commits, pushes, running commands, etc.) without first requesting explicit approval from the user.
- Request approval **before each individual step** in the plan, not just once at the start.
- If the user's response is ambiguous, ask a clarifying question — do not infer approval.

### Rule 3 — Verify All Changes

After completing any change:

1. Review the modified files to confirm they match the stated goals.
2. Run any relevant tests, linters, or build steps (once they exist in the project).
3. Report the verification outcome to the user before considering the task done.
4. If verification reveals a gap, create a follow-up plan in `docs/plans/` and request approval before proceeding.

---

## Git Conventions

| Setting | Value |
|---|---|
| Default development branch | `master` |
| Feature/task branches | `claude/<description>-<session-id>` |
| Commit signing | SSH, key at `/home/claude/.ssh/commit_signing_key.pub` |
| Remote | `origin` |

### Branching Workflow

- All AI-driven work must happen on the branch specified in the task instructions (typically a `claude/` branch).
- Never push to `master` or `main` directly without explicit user permission.
- Always use `git push -u origin <branch-name>`.

### Commit Messages

- Use the imperative mood: "Add feature" not "Added feature".
- Keep the subject line under 72 characters.
- Include a blank line between the subject and any body.

---

## Development Conventions

> This section will grow as the project develops. Document new conventions here as they are established.

### Language / Runtime

Not yet determined. Update this section once the tech stack is chosen.

### Testing

No test framework is configured yet. Once added, document:
- How to run tests
- Where tests live
- Naming conventions

### Linting / Formatting

No linter or formatter is configured yet. Once added, document the commands and config file locations here.

### Environment Variables

No `.env` file or environment variables are required at this time.

---

## Updating This File

Whenever a new convention, tool, or workflow rule is added to the project:

1. Follow Rules 1–3 above (plan → approve → verify).
2. Update the relevant section of this file as part of the same change.
3. Keep this file concise — link to external docs rather than duplicating them.
