"""Demo readiness checks. Offline by default; --live-voice opts into one paid TTS call."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-voice", action="store_true", help="Load root .env and send one synthetic phrase to ElevenLabs (uses credits)")
    parser.add_argument("--output", type=Path, help="Write a JSON readiness report")
    args = parser.parse_args()
    missing = [name for name in ("pytest", "streamlit", "httpx", "docx", "pydantic", "crisis_coach") if importlib.util.find_spec(name) is None]
    if missing:
        print("Missing dependencies: " + ", ".join(missing))
        print('Install with: python -m pip install -e ".[ui,voice,dev]" "python-dotenv[cli]"')
        return 1
    report = {"offline_tests": "not_run", "golden": "not_run", "live_voice": "not_requested", "manual_checks": ["Listen to browser playback", "Record, transcribe, review and submit an answer", "Check browser autoplay and live timer behavior"]}
    env = {key: value for key, value in os.environ.items() if not key.startswith(("ELEVENLABS_", "CRISIS_COACH_", "LANGCHAIN_", "LANGSMITH_"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["LANGSMITH_TRACING"] = "false"
    env["LANGCHAIN_TRACING_V2"] = "false"
    with tempfile.TemporaryDirectory(prefix="crisis-smoke-") as tmp:
        env["CRISIS_COACH_DATA_DIR"] = tmp
        checks = ["tests/unit/test_voice.py", "tests/integration/test_voice_ui.py", "tests/domains/collision/test_safety_gates.py", "tests/integration/test_capture_tools.py", "tests/integration/test_local_knowledge.py", "tests/integration/test_persistence_recovery.py"]
        result = subprocess.run([sys.executable, "-B", "-m", "pytest", *checks, "-q", "-p", "no:cacheprovider"], cwd=ROOT, env=env)
        report["offline_tests"] = "passed" if result.returncode == 0 else "failed"
        golden = Path(tmp) / "golden.json"
        result = subprocess.run([sys.executable, "-B", "-m", "crisis_coach.evaluation.runner", "evals/scenarios/golden.json", "--output", str(golden)], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if golden.exists():
            data = json.loads(golden.read_text(encoding="utf-8"))
            report["golden"] = {"status": "passed" if result.returncode == 0 else "failed", "passed": data["passed"], "failed": data["failed"]}
        else:
            report["golden"] = {"status": "failed", "reason": "Runner did not produce a report"}
    if args.live_voice:
        try:
            from dotenv import load_dotenv
            load_dotenv(ROOT / ".env", override=False)
            from crisis_coach.interfaces.voice.elevenlabs import build_voice_provider
            from crisis_coach.models.responses import Instruction
            provider = build_voice_provider()
            if provider is None:
                report["live_voice"] = {"status": "failed", "reason": "Missing or invalid ElevenLabs configuration"}
            else:
                audio = provider.speak(Instruction(text="This is Dana's synthetic Crisis Coach voice test."))
                report["live_voice"] = {"status": "passed", "audio_bytes": len(audio.data), "media_type": audio.media_type, "note": "API returned audio; listening and microphone checks remain manual"}
        except Exception as exc:
            # Provider errors and configuration exceptions must not expose keys or payloads.
            report["live_voice"] = {"status": "failed", "error_type": type(exc).__name__, "reason": "Check dependencies, credentials, permissions, voice access, network, and credits"}
    rendered = json.dumps(report, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return int(report["offline_tests"] != "passed" or report["golden"]["status"] != "passed" or (args.live_voice and report["live_voice"]["status"] != "passed"))


if __name__ == "__main__":
    raise SystemExit(main())
