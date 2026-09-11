import socket
from pathlib import Path
import pytest
from crisis_coach.evaluation.runner import run_suite, Suite


def test_golden_suite_without_network(monkeypatch):
    def denied(*args,**kwargs): raise AssertionError("Golden scenarios must not use network")
    monkeypatch.setattr(socket.socket,"connect",denied)
    result=run_suite(Path("evals/scenarios/golden.json"))
    assert result["failed"] == 0, result
    assert result["passed"] >= 14
    assert all(row["safety_violations"] == 0 for row in result["scenarios"])
    assert {f"T{i}" for i in range(1,14)} <= {case for row in result["scenarios"] for case in row["source_cases"]}


def test_invalid_scenario_is_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Suite.model_validate({"version":1,"scenarios":[{"id":"invalid","source_cases":[],"steps":[{"action":"event","expect":{}}]}]})


def test_langgraph_golden_parity(monkeypatch):
    pytest.importorskip("langgraph")
    def denied(*args,**kwargs): raise AssertionError("No network in parity evaluation")
    monkeypatch.setattr(socket.socket,"connect",denied)
    result=run_suite(Path("evals/scenarios/golden.json"),backend="langgraph")
    assert result["failed"] == 0, result
