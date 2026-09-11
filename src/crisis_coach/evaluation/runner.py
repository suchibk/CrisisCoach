"""Run versioned scenarios with temporary persistence and fake providers.

python -m crisis_coach.evaluation.runner evals/scenarios/golden.json
"""
import argparse
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from ..models.events import InputEvent
from ..practice.runtime import PracticeRuntime

class Expected(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: dict = Field(default_factory=dict)
    contains: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()
    route: tuple[str, ...] | None = None
    preserve_task: bool = False
    tool_calls: int | None = Field(default=None, ge=0)

class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["text", "event", "advance", "photo", "reopen"] = "text"
    text: str | None = None
    event: InputEvent | None = None
    seconds: float = Field(default=0, ge=0, allow_inf_nan=False)
    photo: Literal["usable", "retake"] | None = None
    expect: Expected

    @model_validator(mode="after")
    def required_payload(self):
        if self.action == "text" and self.text is None: raise ValueError("Text step needs text")
        if self.action == "event" and self.event is None: raise ValueError("Event step needs event")
        if self.action == "photo" and self.photo is None: raise ValueError("Photo step needs fixture")
        return self

class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    source_cases: tuple[str, ...]
    initial: Expected = Field(default_factory=Expected)
    steps: tuple[Step, ...] = Field(min_length=1)

class Suite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: Literal[1]
    scenarios: tuple[Scenario, ...]

    @model_validator(mode="after")
    def unique_ids(self):
        if len({s.id for s in self.scenarios}) != len(self.scenarios): raise ValueError("Duplicate scenario IDs")
        return self


def _path(data, path):
    value = data
    for key in path.split("."):
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def check(expected, runtime, reply, previous=None, tool_calls=0):
    data = runtime.scene.model_dump(mode="json")
    errors = []
    for key, value in expected.state.items():
        try: actual = _path(data, key)
        except (KeyError, IndexError): actual = "<missing>"
        if actual != value: errors.append(f"{key}: expected {value!r}, got {actual!r}")
    text = reply.text if reply else ""
    for fragment in expected.contains:
        if fragment not in text: errors.append(f"Response missing {fragment!r}")
    for fragment in expected.excludes:
        if fragment in text: errors.append(f"Response contains prohibited {fragment!r}")
    if expected.route is not None and runtime.coach.last_route != expected.route:
        errors.append(f"Unexpected graph route {runtime.coach.last_route}")
    if expected.preserve_task and previous is not None:
        for key in ("current_evidence_id", "timer_deadline", "last_instruction"):
            if data[key] != previous[key]: errors.append(f"Changed preserved field: {key}")
    if expected.tool_calls is not None and expected.tool_calls != tool_calls:
        errors.append(f"Expected {expected.tool_calls} tool calls; got {tool_calls}")
    return errors


def _run_suite(path: Path, backend="local"):
    suite = Suite.model_validate_json(path.read_text(encoding="utf-8"))
    results = []
    for scenario in suite.scenarios:
        errors = []
        tool_count = 0
        safety_violations = 0
        with PracticeRuntime(backend=backend) as runtime:
            errors.extend(check(scenario.initial, runtime, runtime.first))
            for number, step in enumerate(scenario.steps, 1):
                previous = runtime.scene.model_dump(mode="json")
                offset = len(runtime.audit.calls)
                try:
                    if step.action == "text": reply = runtime.coach.turn(runtime.scene, step.text)
                    elif step.action == "event": reply = runtime.coach.handle_event(runtime.scene, step.event)
                    elif step.action == "advance":
                        runtime.clock.advance(step.seconds)
                        reply = runtime.coach.poll(runtime.scene)
                    elif step.action == "photo": reply = runtime.capture(step.photo)
                    else:
                        runtime.scene, reply = runtime.coach.reopen(runtime.scene.incident_id)
                    calls = len(runtime.audit.calls) - offset
                    tool_count += calls
                    # A safety stop must not mutate evidence or perform a tool.
                    if reply and reply.terminate and runtime.scene.status.value == "stood_down":
                        if calls or runtime.scene.model_dump(mode="json")["evidence"] != previous["evidence"]:
                            safety_violations += 1
                            errors.append(f"step {number}: safety side effect")
                    errors.extend(f"step {number}: {e}" for e in check(step.expect, runtime, reply, previous, calls))
                except Exception as exc:
                    errors.append(f"step {number}: {type(exc).__name__}: {exc}")
                    break
        results.append({"id":scenario.id, "source_cases":scenario.source_cases, "status":"failed" if errors else "passed", "errors":errors, "tool_calls":tool_count, "safety_violations":safety_violations})
    return {"version":suite.version, "backend":backend, "passed":sum(r["status"] == "passed" for r in results), "failed":sum(r["status"] == "failed" for r in results), "scenarios":results,
        "manual_checks":[{"id":"T14", "status":"separate browser suite", "reason":"Appearance and real device behavior are not engine assertions"}, {"id":"voice-device", "status":"pending", "reason":"Real microphone/playback requires manual device testing"}, {"id":"domain-review", "status":"pending", "reason":"Independent safety policy review"}]}


def run_suite(path: Path, backend="local"):
    if backend == "langgraph":
        from langsmith import tracing_context
        with tracing_context(enabled=False):
            return _run_suite(path, backend)
    return _run_suite(path, backend)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("suite", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--backend", choices=("local","langgraph"), default="local")
    args = parser.parse_args()
    result = run_suite(args.suite, args.backend)
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 1 if result["failed"] else 0

if __name__ == "__main__": raise SystemExit(main())
