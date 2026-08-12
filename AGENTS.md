# AGENTS.md

## Project

This repository implements an AI Agent Harness using the OpenAI Agents SDK.

The project is developed incrementally as an MVP.

## Working Rules

- Read `ARCHITECTURE.md` before making architectural changes.
- Read `PROJECT.md` to understand the current implementation stage.
- Preserve existing architectural boundaries.
- Do not introduce abstractions or infrastructure for future components unless explicitly requested.
- Make the smallest coherent change required for the current task.
- Do not refactor unrelated code.
- Use type hints and keep implementations explicit and testable.
- Add or update tests when behavior changes.
- Run relevant tests after implementation.

## Documentation

After completing a meaningful implementation step:

- Update `ARCHITECTURE.md` only if the actual architecture or layer responsibilities changed.
- Update `PROJECT.md` when project progress changes.
- Do not modify `AGENTS.md` unless repository-wide working rules change.