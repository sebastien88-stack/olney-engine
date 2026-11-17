"""Export an Olney interpretation context as JSON for UI/LLM development."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
import json
import sys


PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from olney_engine import OlneyEngine
from interpretation_validation import validate_context


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("birth_date", help="YYYY-MM-DD or DD/MM/YYYY")
    parser.add_argument("target_date", help="YYYY-MM-DD or DD/MM/YYYY")
    parser.add_argument("--time", dest="target_time")
    parser.add_argument("--place", dest="target_place")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--focus", default="general", choices=["general", "natal", "life_path", "year", "fifty_two_days", "week", "day", "hour"])
    parser.add_argument("--profile-id", help="Identifiant stable pour isoler la mémoire d’un profil")
    parser.add_argument("--mode", default="current", choices=["current", "cycle"], help="Lecture actuelle ou parcours complet du cycle choisi par --focus")
    args = parser.parse_args()

    if (args.target_time is None) != (args.target_place is None):
        parser.error("--time and --place must be provided together")

    engine = OlneyEngine()
    context = engine.tool_get_interpretation_context(
        args.birth_date,
        args.target_date,
        args.target_time,
        args.target_place,
        reading_focus=args.focus,
        profile_id=args.profile_id,
        reading_mode=args.mode,
    )
    validate_context(context)
    rendered = json.dumps(context, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
