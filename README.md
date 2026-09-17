# DynosAI Core

DynosAI Core is the reusable core of DynosAI.

The project is developed incrementally: each step adds one small, complete, tested capability while keeping the repository usable and releasable.

> **Status:** Early development  
> **Current release:** `v0.0.3`

## Current capabilities

Version `0.0.3` provides:

- Installable Python distribution: `dynosai-core`
- Python import namespace: `dynosai`
- Command-line entry point: `dynos`
- Deterministic version reporting with `dynos --version`
- Automated offline tests
- Buildable wheel and source distributions
- Read-only operating-directory resolution with `dynosai.directory.resolve_operating_directory`
- Read-only Git availability and working-tree relationship inspection through `dynosai.git.inspect_git_relationship`
- Git-specific reporting of working-tree roots, including root-versus-descendant relationships
- Standard `ValueError`, `FileNotFoundError`, and `NotADirectoryError` failures for invalid directory inputs

Git inspection does not modify repositories or filesystem state, contact remotes, require network access or credentials, or create project state. Spec Kit integration, Grok Build integration, execution runtimes, persistence, service APIs, and application functionality are not part of `0.0.3`.

## Requirements

- Python 3.11 or newer

## Development

Synchronize the development environment:

```bash
uv sync
```
