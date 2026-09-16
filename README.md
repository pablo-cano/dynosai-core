\# DynosAI Core



DynosAI Core is the reusable core of DynosAI.



The project is being developed incrementally, with each release adding one

small, complete, verified capability.



\## Current version



\*\*0.0.1 — Core Package Bootstrap\*\*



The current release provides:



\- an installable Python package named `dynosai-core`;

\- the Python import namespace `dynosai`;

\- the `dynos` command-line entry point;

\- deterministic version reporting through `dynos --version`;

\- automated offline tests;

\- buildable wheel and source distributions.



No project inspection, Git integration, Spec Kit integration, Grok Build

integration, execution runtime, persistence, service API, or application

functionality is included yet.



\## Requirements



\- Python 3.11 or newer



\## Development setup



Clone the repository and synchronize the development environment:



```bash

uv sync

