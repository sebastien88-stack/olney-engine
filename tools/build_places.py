"""Build the compact offline city index bundled with Olney Engine."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path


def main(source_zip: Path, destination: Path) -> None:
    places = []
    with zipfile.ZipFile(source_zip) as archive:
        with archive.open("cities5000.txt") as source:
            for raw_line in source:
                fields = raw_line.decode("utf-8").rstrip("\n").split("\t")
                if len(fields) < 19 or fields[6] != "P":
                    continue
                places.append([
                    fields[1],
                    fields[2],
                    fields[8],
                    round(float(fields[4]), 5),
                    round(float(fields[5]), 5),
                    fields[17],
                    int(fields[14] or 0),
                ])

    places.sort(key=lambda item: (-item[6], item[0], item[2]))
    destination.write_text(
        json.dumps(places, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"{len(places)} places written to {destination}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
