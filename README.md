# DynosAI Core

DynosAI Core is the reusable core of DynosAI.

The project is developed incrementally: each step adds one small, complete, tested capability while keeping the repository usable and releasable.

> **Status:** Early development  
> **Current release:** `v0.0.1`

## Current capabilities

Version `0.0.1` provides:

- Installable Python distribution: `dynosai-core`
- Python import namespace: `dynosai`
- Command-line entry point: `dynos`
- Deterministic version reporting with `dynos --version`
- Automated offline tests
- Buildable wheel and source distributions

Project inspection, Git integration, Spec Kit integration, Grok Build integration, execution runtimes, persistence, service APIs, and application functionality are not part of `0.0.1`.

## Requirements

- Python 3.11 or newer

## Development

Synchronize the development environment:

```bash
uv sync