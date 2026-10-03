# Tabula Peutingeriana Explorer

An interactive map of the Tabula Peutingeriana, the Roman road map that survives in a medieval copy. Pick any place and switch between the Table itself and a modern OpenStreetMap view.

**Live:** https://cyberhirsch.github.io/peutinger-map/

- **Peutinger view:** the full roll from Britain to India, using Konrad Miller's 1887 facsimile (cut into 13 image strips).
- **OpenStreetMap view:** the same places at their real-world locations, with the Table's road network drawn over a modern map.
- About 3,000 places can be searched by Latin or modern name. Each place shows the spelling used on the Table, its modern name, and its roads to neighbouring places with the Table's distances.

## Running it

The page loads its image strips and `places.json` over HTTP, so serve the folder rather than opening the file directly:

```bash
python3 -m http.server 8791
```

Then open http://localhost:8791.

## How places were located on the scan

Each marker is coloured by how it was placed:

| Colour | Method |
|---|---|
| Blue | Placed by hand (58 major cities) |
| Green | Label read on the scan with OCR (macOS Vision), fuzzy-matched to the place list, and only accepted if a neighbouring place on the same road is nearby |
| Orange | Estimated along the road between placed neighbours, using the Table's own distances |
| Grey | Not placed on the scan (OpenStreetMap view only) |

The red road lines were also traced from the scan (`tools/trace.py`) and used to snap markers onto roads.

**Work in progress:** placements are being checked against the grid squares in Talbert's *Rome's World* database. A visual review of every marker will follow.

## Sources and licences

- **Scan:** Konrad Miller, *Castori Romanorum Cosmographi Tabula quae dicitur Peutingeriana* (Ravensburg, 1887). Public domain.
- **Places and roads:** [OmnesViae](https://omnesviae.org) by René Voorburg, based on Richard J. A. Talbert, *Rome's World: The Peutinger Map Reconsidered* (Cambridge University Press, 2010). `places.json` is derived from the OmnesViae dataset, which is MIT-licensed; see [LICENSE-omnesviae.txt](LICENSE-omnesviae.txt).
- **Modern map:** © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
- **Map library:** [Leaflet](https://leafletjs.com).

## Files

- `index.html`: the app.
- `places.json`: places (Table spelling, modern name, real-world coordinates, position on the scan, how it was placed) and roads (pairs of places with distances).
- `strip_00.jpg` to `strip_12.jpg`: the scan, cut into 2048-px-wide strips.
- `tools/`: the extraction scripts (road tracing, OCR, matching). They're currently written for a local working folder and need path changes before they can be re-run.
