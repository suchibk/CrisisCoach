# Golden scenario evaluation

Run from the repository root:

```powershell
python -m crisis_coach.evaluation.runner evals/scenarios/golden.json --output evals/results/golden.json
python -m crisis_coach.evaluation.runner evals/scenarios/golden.json --backend langgraph --output evals/results/golden-langgraph.json
python -B -m pytest
```

The runner validates scenario records with Pydantic, uses the shared workflow, injects monotonic and UTC clocks, stores data in temporary SQLite/attachment directories, and uses explicit local photo fakes. It ignores configured AI/voice providers and custom source directories. LangGraph evaluation disables tracing. The test suite also blocks sockets during golden runs.

Each scenario has source T-case IDs, an initial expectation, and typed steps (text, event, clock advance, fixture photo, or reopen). Assertions compare state paths, graph routes, response fragments, preserved tasks/deadlines, and attempted local tool calls. Safety termination must not mutate evidence or call a tool. Failures give a nonzero CLI exit status. Manual/expert checks remain separate in the JSON output. Changing expectations requires reviewing the source mapping, not merely accepting a new snapshot.

Browser acceptance:

```powershell
python -m pip install -e ".[ui,dev,browser]"
python -m playwright install chromium
$env:CRISIS_COACH_BROWSER_TESTS='1'
$env:CRISIS_COACH_SCREENSHOTS='evals/results/ui'
python -B -m pytest tests/browser
```

The browser test launches a temporary localhost Streamlit server, clears provider configuration, blocks external browser requests, uses synthetic practice inputs, checks desktop/mobile layouts and themes, uploads a fixture, and downloads/opens a real DOCX. It closes the browser/server after the test. The normal pytest run skips this opt-in browser test.

See [acceptance report](../docs/golden-acceptance-report.md) for the tested environment, adapted T1-T14 outcomes, screenshots, and outstanding manual checks.
