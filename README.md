# Tabula Peutingeriana Explorer

An interactive map of the Tabula Peutingeriana, the Roman road map that survives in a medieval copy. Pick any place and switch between the Table itself and a modern OpenStreetMap view.

**Live:** https://cyberhirsch.github.io/peutinger-map/

- **Peutinger view:** the full roll from Britain to India, using Konrad Miller's 1887 facsimile (cut into 13 image strips).
- **OpenStreetMap view:** the same places at their real-world locations, with the Table's road network drawn over a modern map.
- About 3,200 places can be searched by Latin or modern name; 2,702 of them are marked on the scan. Each place shows the spelling used on the Table, its modern name, its Talbert grid square, and its roads to neighbouring places with the Table's distances.

## Running it

The page loads its image strips and `places.json` over HTTP, so serve the folder rather than opening the file directly:

```bash
python3 -m http.server 8791
```

Then open http://localhost:8791.

## How places were located on the scan

1. **Hand-placed anchors.** 58 major cities were placed by hand.
2. **Reading the labels.** The scan was read with OCR (macOS Vision, two passes at different scales). Each name read was fuzzy-matched to the place list, but a match only counted if it fell inside the grid square that Talbert's *Rome's World* database gives for that place. Talbert's grid squares were mapped onto Miller's sheets: a segment is one of Miller's sheets, its five columns are equal fifths of the sheet, and its three rows are thirds of the map's height.
3. **Estimates.** The remaining places were estimated along the road between already-placed neighbours, using the Table's own distances, or else put somewhere inside their grid square.
4. **Visual review.** Every marker was checked on numbered crops of the scan, one reviewer per Talbert segment. Each wrong or estimated marker was moved to the start of its actual label, and a second, independent checker re-examined every correction before it was applied.

Each marker is coloured by the result:

| Colour | Meaning | Places |
|---|---|---|
| Blue | Placed by hand | 46 |
| Green | Label found on the scan and visually confirmed | 2,643 |
| Orange | Estimated along the road (label illegible, or an unnamed station) | 4 |
| Purple | Somewhere in its Talbert grid square (label not found) | 9 |
| Grey | Not on the surviving Table: the lost western end, filled in by OmnesViae from the Antonine Itinerary. OpenStreetMap view only | |

The red road lines were also traced from the scan (`tools/trace.py`), and the traced roads guided the estimates.

## Sources and licences

- **Scan:** Konrad Miller, *Castori Romanorum Cosmographi Tabula quae dicitur Peutingeriana* (Ravensburg, 1887). Public domain.
- **Places and roads:** [OmnesViae](https://omnesviae.org) by René Voorburg, based on Richard J. A. Talbert, *Rome's World: The Peutinger Map Reconsidered* (Cambridge University Press, 2010). `places.json` is derived from the OmnesViae dataset, which is MIT-licensed; see [LICENSE-omnesviae.txt](LICENSE-omnesviae.txt).
- **Grid squares:** the segment-grid references (e.g. Roma = 4B5) come from the online database accompanying *Rome's World*, consulted via the Internet Archive.
- **Modern map:** © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
- **Map library:** [Leaflet](https://leafletjs.com).

## Files

- `index.html`: the app.
- `places.json`: places (Table spelling `n`, modern name `m`, real-world coordinates `ll`, position on the scan `xy`, how it was placed `c`, Talbert grid square `g`) and roads (pairs of places with distances).
- `strip_00.jpg` to `strip_12.jpg`: the scan, cut into 2048-px-wide strips.
- `tools/`: the extraction scripts: road tracing (`trace.py`), OCR (`ocr.swift`), grid model (`grid.py`), grid-constrained matching (`ocrmatch2.py`), review crops and contact sheets (`render_review.py`, `render_points.py`, `zoom.py`), applying the review (`apply_review.py`) and building `places.json` (`build_places.py`). They're written for a local working folder and need path changes before they can be re-run.
