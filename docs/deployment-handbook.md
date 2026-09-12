# Crisis Coach deployment and demonstration handbook

## Deployment scope

This handbook runs the current prototype on a presenter's Windows machine with a local Streamlit UI, local SQLite storage, and optional ElevenLabs requests. It also describes requirements for a hosted demo; it does not provision cloud resources. Only the collision domain is implemented.

Use Python 3.11 or newer and run commands from the repository root. For screen-by-screen instructions, see the [illustrated ElevenLabs guide](../demo/README.md).

## Install and configure

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[ui,voice,dev]" "python-dotenv[cli]"
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
notepad .env
```

Set these entries in `.env`:

```dotenv
ELEVENLABS_API_KEY=your_secret_key
ELEVENLABS_VOICE_ID=your_account_voice_id
ELEVENLABS_TTS_MODEL=eleven_multilingual_v2
ELEVENLABS_STT_MODEL=scribe_v2
CRISIS_COACH_GRAPH_BACKEND=local
CRISIS_COACH_DATA_DIR=.local-data/dana-demo
```

The data directory above isolates demo incidents from the default application-data directory. It is relative to the launch directory. Keep optional `CRISIS_COACH_AI_*` settings empty for a deterministic demo. `.env` is ignored by Git; `.env.example` must contain placeholders only. [Credential creation instructions](../demo/README.md#2-get-your-elevenlabs-credentials).

The app reads process environment variables. The following launcher loads `.env`; an existing process environment value takes precedence. Credentials entered through the voice UI take precedence for that browser session.

## Run and stop

```powershell
.\.venv\Scripts\python.exe -m dotenv run -- .\.venv\Scripts\python.exe -m streamlit run src/crisis_coach/interfaces/streamlit_app.py --server.address=127.0.0.1 --server.port=8501
```

Open `http://localhost:8501`. Stop the server with Ctrl+C. Restart after environment changes, then refresh the browser. Use the same Python executable for install, tests, and startup; this avoids PATH and virtual environment mismatches.

Optional process health check while the app is running:

```powershell
Invoke-WebRequest -Uri http://localhost:8501/_stcore/health | Select-Object StatusCode, Content
```

A successful HTTP response checks server availability only. It does not verify account credentials, microphone access, persistence, or workflow behavior.

## Automated deployment smoke test

Run the supplied [smoke-test script](../scripts/demo_smoke.py):

```powershell
.\.venv\Scripts\python.exe -B scripts/demo_smoke.py --output .local-data/readiness.json
```

It checks required imports, runs selected safety/voice/UI/tool/retrieval/recovery tests, then executes the golden scenario suite. Offline subprocesses clear application/provider configuration, use temporary storage, and do not load `.env`. Voice responses are simulated. The script exits 0 only if all requested checks pass; a failure exits nonzero. The JSON report retains manual device checks as outstanding. No running Streamlit server is needed.

Optional real provider smoke test:

```powershell
.\.venv\Scripts\python.exe -B scripts/demo_smoke.py --live-voice --output .local-data/readiness-live.json
```

`--live-voice` explicitly sends one fixed synthetic phrase to ElevenLabs and consumes credits. It loads the root `.env` without overriding existing environment values. It checks that the provider returns nonempty MPEG audio, reports byte count, and does not save the audio or print credentials. It does not play sound or test transcription. A failed live check also makes the exit code nonzero.

To run all ordinary tests:

```powershell
.\.venv\Scripts\python.exe -B -m pytest
```

For optional browser acceptance and LangGraph evaluation commands, see [evaluation instructions](../evals/README.md).

## Manual acceptance script

Use fictional details. In **Live incident > Incident**, enable voice after each New incident; permissions reset per incident.

| Test | Steps | Pass condition |
| --- | --- | --- |
| Real TTS | Enable speech playback; Prepare spoken response; press Play. | Displayed coach response is audible. |
| Real STT | Enable recording transcription; record a short answer; send to ElevenLabs. | Transcript appears and matches the recording after review/edit. |
| Human review | Inspect the transcript before pressing Send reviewed answer. | Incident does not advance until you submit the reviewed text. |
| Happy path | New incident; answer No, No, Yes to the three safety questions. | Evidence instruction appears; new response can be spoken. |
| Capture tool | Upload a synthetic image through the requested capture control. | Stored evidence appears; typing photo taken alone is not an upload. |
| Unknown path | New incident; answer I'm not sure, then I don't know. | Collection stops; no evidence tool is offered. |
| Re-entry denial | Click Reopen this incident, then answer No. | Acknowledgment explains coaching remains paused without asking the same question again. |
| Persistence | Reopen the saved stopped incident. | Its safety restriction remains in force. |

The live safety timeout is eight seconds per unanswered prompt; timers continue during audio generation and review. Rehearse before presenting. Pause while explaining; use short answers after resuming. If timing interrupts the walkthrough, verify the deterministic path with typed answers and demonstrate transcription separately. Practice mode is offline with a manual clock and cannot prove real voice connectivity.

## Hosted demo boundary

The tested path here is localhost. For access from another machine, a deployment would need a server environment with the same dependencies, an app process, and durable writable storage configured through an absolute `CRISIS_COACH_DATA_DIR`. Supply credentials through the hosting service's secret configuration, not a committed `.env`.

Browser microphone use requires a secure context, so use HTTPS for a remote demo. This prototype does not implement user authentication or per-user incident authorization: do not expose its saved-incident UI publicly with real data. An access-controlled demo host and synthetic data are required before sharing remotely. Multiple independent replicas with separate local SQLite files do not provide shared incident state; a multi-user storage/auth design is future work.

## Data, restart, and rollback

The data directory contains SQLite databases, attachments, and exports. Voice audio is transient, while reviewed transcript text becomes incident data. Profile data and saved incident IDs can appear in the UI; use a fresh demo directory for presentations.

Before an upgrade, stop the app and copy the entire data directory to a backup location, retaining databases and attachments together. Record the working Git revision and Python dependency versions. To roll back, stop the app, restore the known working code/environment and matching data backup, then rerun the smoke checks. Schema backward compatibility is not guaranteed by this prototype. No backup or deletion is performed automatically by the supplied script.

## Troubleshooting

- **dotenv not recognized:** use `python.exe -m dotenv` as shown above.
- **Configured but silent:** configuration is not an API test. Prepare speech and press Play; check player volume, tab mute, and output device.
- **Provider warning:** check permissions for TTS/STT, voice access, credits, and network; change credentials or retry manually.
- **Unexpected stand-down:** safety timers may have expired during explanation; start a fresh synthetic incident.
- **Repeated saved-state restriction:** New incident starts fresh; reopening intentionally preserves prior stand-down.
- **Storage error:** stop progressing and check that the configured data directory is writable; reopen after resolving it.

[Presentation notes and implemented agentic concepts](demo-presentation.md)
