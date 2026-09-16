"""Command-line entry point for the `dynos` executable."""

import argparse

import dynosai


def main() -> None:
    parser = argparse.ArgumentParser(prog="dynos", add_help=False)
    parser.add_argument(
        "--version",
        action="version",
        version=f"dynos {dynosai.__version__}",
    )
    parser.parse_args()
