# Solarpanels — Agent Instructions

## Repo state
Empty scaffold. No source code, README, or build config yet.

## Agent rules (read these)
- `.agents/rules/00_antigravity_protocol.md` — efficiency protocol, Mode A/B/C workflow
- `.agents/rules/01_agent_planning.md` — planning protocol (plan before act, versioned plans)
- `.agents/rules/20_python_tooling.md` — Python toolchain constraints (see below)

## Always-loaded skills
Defined in `.agents/skills/index.json` (9 skills enforced on every prompt):
code-documenter, postgres-best-practices, postgres-patterns, python-pro,
python-testing-patterns, python-testing, react-expert, react-patterns,
react-testing, secure-code-guardian

## Python tooling (from rule 20)
- package mgmt: `uv` (not pip)
- lint/format: `ruff` (not black)
- type check: `ty` (not mypy)
- deps go in `pyproject.toml`, not `requirements.txt`
- Python >=3.12, modern syntax required (`X | Y`, `list[T]`, structural pattern matching)

## No existing commands
No `package.json`, `pyproject.toml`, or test config yet — first task likely needs bootstrapping.
