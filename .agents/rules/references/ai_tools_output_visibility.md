# Python Overlay

## Python Workflow

- Prefer the project-managed environment and commands from `pyproject.toml`,
  lockfiles, task runners, or the README.
- Keep package metadata, console scripts, and import paths consistent.
- Use standard-library functionality where it is adequate.
- Keep installed CLI behavior and direct module behavior consistent when both
  entrypoints are advertised.
- Preserve text output contracts for piped output; terminal color, links, or
  progress UI must be guarded by TTY detection.

## Testing and Quality

- Run the narrowest relevant tests first, then broader checks when shared
  behavior changes.
- Run formatting, linting, and type checks only through project-approved tools.
- Avoid adding runtime dependencies for simple scripting problems unless the
  dependency already exists or the tradeoff is documented.
- Use the repository's aggregate validation command when available. Otherwise
  run applicable lint, format, type, import, and test checks for the changed
  package layout.

## Packaging

- When changing public CLI behavior, update help text, README examples, and
  changelog or release notes if the project uses them.
- When cutting a release, update every version source of truth used by the
  project and verify version-reporting smoke checks.

## Data Tool Safety

- Treat generated data, active input files, exports, reports, and local caches
  as potentially sensitive unless the repository explicitly says otherwise.
- Keep private operational inputs ignored. Commit structural templates with
  placeholder data instead.
- For tools that mutate files or external systems, prefer dry-run or preview
  modes and require explicit apply intent.
