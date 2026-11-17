# Third-party data notices

## GeoNames geographical database

`places.json` is derived from the GeoNames `cities5000` geographical database.

- Source: https://download.geonames.org/export/dump/
- Copyright: GeoNames contributors
- License: Creative Commons Attribution 4.0
- License text: https://creativecommons.org/licenses/by/4.0/

The data is bundled as an offline city, coordinate and IANA-timezone index.
It is transformed by `tools/build_places.py`: populated-place entries are
selected, coordinates rounded, fields reduced and entries sorted by population.

## IANA timezone database via tzdata

The bundled `tzdata` package is maintained by the Python Software Foundation
and provides the IANA timezone database on systems that do not include it.

- Project: https://github.com/python/tzdata
- License: Apache License 2.0

The underlying IANA timezone dataset retains its own public-domain/source notices:
https://www.iana.org/time-zones/tz-link

The application also relies on Python and Tcl/Tk. Retain the notices of the
exact runtime versions bundled in any future binary distribution. Build tools
are not relicensed by the project's GPL grant. See `LICENSING.md` for scope and
resource-provenance checks, including materials not cleared for relicensing.
