from __future__ import annotations

from ..domains.collision import CollisionWorkflow
from ..domains.collision.ai import build_optional_injury_classifier


def main() -> None:
    coach = CollisionWorkflow(ai_classifier=build_optional_injury_classifier())
    state, instruction = coach.start()
    print(f"Crisis Coach: {instruction.text}")
    while not instruction.terminate:
        try:
            user_text = input(f"{state.person_name}: ")
        except (EOFError, KeyboardInterrupt):
            print("\nCrisis Coach: Stopping. Everything so far is saved.")
            break
        instruction = coach.turn(state, user_text)
        print(f"Crisis Coach: {instruction.text}")


if __name__ == "__main__":
    main()
