# Licensing scope and outstanding checks

Copyright (c) 2026 Sébastien and contributing authors for their original code.

## Original source code

Original first-party Python code, build scripts, tests, examples and GitHub
configuration in this repository are offered under **GPL-3.0-only**, the GNU
General Public License version 3. The complete text is in [LICENSE](LICENSE).
The Python files under `tzdata/` are third-party code and are excluded from this
grant. Contributor submissions must be compatible with this license.

GPL does not prohibit commercial use. Distribution of covered modified code or
binaries requires compliance with its terms, including corresponding-source and
notice obligations. No assignment of contributor copyright is required.

## Separate resources

| Material | Treatment in this preparation |
| --- | --- |
| `places.json` | GeoNames-derived data, CC BY 4.0; retain attribution and identify transformation |
| `tzdata/` | Third-party package under Apache-2.0; underlying IANA data retain their own public-domain/source notices |
| `data.json` | Canonical series extracted from workbook Feuil2/Feuil3; provenance and redistribution rights require maintainer confirmation |
| `interpretation/**` | Mixed original editorial writing, validated conventions, book-derived terms/excerpts; not blanket-relicensed by this PR |
| `assets/**` | Logo and recreated historical artwork; not blanket-relicensed; original-artwork rights require review |
| `docs/screenshots/**` | User-supplied screenshots approved for the existing public README; not blanket-relicensed |
| `README*`, `docs/**`, `BACKEND_LECTURE.md`, release notes | Project documentation may quote or describe mixed sources; no blanket content relicensing |
| Future Historical Atlas | Not present or published; no license granted by this preparation |

For excluded original material, existing rights remain reserved pending an
explicit content-license decision. For third-party material, the holder's
actual terms control. Public visibility is not evidence of relicensing rights.
This file does not impose proprietary restrictions on GPL-covered source code.

The maintainer's confirmation covers original project code, not ownership of
source books, workbook material of unknown authorship or historical artwork.
Before describing the **whole distribution** as open source, resolve the
outstanding rows or replace/exclude those resources with suitable alternatives.
The current app requires the calculation data and interpretation corpus;
this PR does not remove them or refactor the loader.

## Distribution and prior releases

No past tag is changed. Existing 1.8.5/1.8.6 releases keep their old notices.
Before the next binary release, close the resource-rights checklist, bundle
LICENSE, this scope document and third-party notices, and provide corresponding
source for the exact release. Review Python/Tcl/Tk runtime notices in the
packaged output as well. No new binary is built or released by this PR.

## References

- https://www.gnu.org/licenses/gpl-3.0.html
- https://www.gnu.org/licenses/license-list.html#apache2
- https://creativecommons.org/licenses/by/4.0/
- https://github.com/python/tzdata
- https://data.iana.org/time-zones/tz-link.html

The GPL text was obtained from the SPDX license-list-data mirror of
GPL-3.0-only, preserving the complete license and application appendix:
https://github.com/spdx/license-list-data/blob/main/text/GPL-3.0-only.txt
