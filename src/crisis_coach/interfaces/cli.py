from __future__ import annotations

import argparse
from queue import Queue, Empty
from threading import Thread
from ..bootstrap import build_coach, build_repository
from ..persistence.contracts import PersistenceError


def main() -> None:
    parser = argparse.ArgumentParser(description="Local collision coaching")
    parser.add_argument("--incident", help="Reopen a saved incident ID")
    parser.add_argument("--list", action="store_true", help="List saved incidents")
    args = parser.parse_args()
    try:
        if args.list:
            for incident in build_repository().list_incidents():
                print(f"{incident.incident_id}  {incident.person_name}  {incident.status.value}")
            return
        coach = build_coach()
        state, instruction = coach.reopen(args.incident) if args.incident else coach.start()
    except (PersistenceError, KeyError) as exc:
        parser.exit(1, f"Cannot open incident: {exc}\n")
    print(f"Incident: {state.incident_id}")
    incoming: Queue[str | None] = Queue()

    def read_input() -> None:
        while True:
            try:
                incoming.put(input())
            except EOFError:
                incoming.put(None)
                return

    print("Controls: stop, go on, repeat, slow down, /export. Ctrl+C exits.")
    print(f"Crisis Coach: {instruction.text}")
    Thread(target=read_input, daemon=True).start()
    try:
        while not instruction.terminate:
            try:
                text = incoming.get(timeout=coach.seconds_until_timer(state))
            except Empty:
                reply = coach.poll(state)
            else:
                if text is None:
                    break
                reply = coach.turn(state, text)
            if reply is not None:
                instruction = reply
                print(f"Crisis Coach: {reply.text}")
                if state.exports and reply.reason == state.exports[-1].relative_path:
                    from ..config import AppSettings
                    print(f"Evidence pack: {AppSettings().data_dir / 'exports' / reply.reason}")
    except PersistenceError:
        print("Storage unavailable or incident changed. Reopen the incident before continuing.")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
