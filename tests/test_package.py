"""Tests for the dynosai package import surface and version identity (FR-002, FR-005, FR-006)."""

import importlib
import importlib.metadata

import dynosai

EXPECTED_VERSION = "0.0.3"


def test_import_succeeds() -> None:
    assert importlib.import_module("dynosai") is dynosai


def test_version_attribute_is_expected_value() -> None:
    assert dynosai.__version__ == EXPECTED_VERSION


def test_version_matches_distribution_metadata() -> None:
    assert importlib.metadata.version("dynosai-core") == dynosai.__version__ == EXPECTED_VERSION
