# Tabula Peutingeriana Explorer

An interactive map of the Tabula Peutingeriana, the Roman road map that survives in a medieval copy. Pick any place and switch between the Table itself and a modern OpenStreetMap view.

**Live:** https://cyberhirsch.github.io/peutinger-map/

- **Peutinger view:** the full roll from Britain to India, using Konrad Miller's 1887 facsimile (cut into 13 image strips).
- **OpenStreetMap view:** the same places at their real-world locations, with the Table's road network drawn over a modern map.
- About 3,200 places can be searched by Latin or modern name. All 2,702 places on the surviving Table are marked on the scan. Each place shows the spelling used on the Table, its modern name, its Talbert grid square, a confidence rating, links to Vici.org, Pleiades, Wikidata, Livius and DARE, and its roads to neighbouring places with the Table's distances.

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

5. **The last 13.** The last 13 places had no readable label: 11 unnamed or illegible road stations, Rome's harbour (Portus, drawn without a name), and the faint Viratedo. They were located by comparing Miller's copy with photos of the original manuscript and following the road from the confirmed neighbours. Each was then checked independently.

Each marker is coloured by the result:

| Colour | Meaning | Places |
|---|---|---|
| Blue | Placed by hand | 46 |
| Green | Found on the scan (label or symbol) and visually confirmed | 2,645 |
| Teal | Unnamed station, placed from the road layout | 11 |
| Grey | Not on the surviving Table: the lost western end, filled in by OmnesViae from the Antonine Itinerary. OpenStreetMap view only | |

## Confidence ratings

Every place on the scan has a confidence score from 0 to 100. The info panel shows the score and the reasons behind it, and the "colour by" switch colours the markers by confidence.

| Band | Score | Typical evidence |
|---|---|---|
| High | 85–99 | Label read on the scan and confirmed by eye, or moved to its label by a reviewer and checked independently |
| Medium | 65–84 | Spelling on Miller's copy differs from Talbert's reading, the position was set by the checker alone, or it is an unnamed station placed from the road layout |
| Low | 40–64 | Unnamed station where the checker was only moderately sure |
| Very low | under 40 | Not confirmed (currently none) |

Points are deducted for falling outside the place's Talbert grid square, being implausibly far from its road neighbours, or sharing a spot with another place. Current totals: 2,638 high, 61 medium, 2 low.

The scores were calibrated by hand-checking samples against the scan. 36 of 36 reviewer corrections and 18 of 18 reviewer confirmations of weak OCR matches were correct, and so were all 13 of the last places.

The **real-world location** is rated separately from OmnesViae's data: *identified* (a modern place is given), *approximate* (OmnesViae marks it with "~", or gives no modern name) or *unknown* (no coordinates).

The red road lines were also traced from the scan (`tools/trace.py`), and the traced roads guided the estimates.

## Linked identifiers

Places are linked to other gazetteers of the ancient world. Counts are for the 2,701 places on the scan:

| Identifier | Places | Source of the link |
|---|---|---|
| [Pleiades](https://pleiades.stoa.org) | 2,475 | Pleiades' own citations of Talbert's database, Vici.org links, and name-and-distance matching |
| [Vici.org](https://vici.org) | 2,044 | Vici's OmnesViae import (`skos:exactMatch`), or a Vici record that shares the Pleiades id; curated Vici records are preferred |
| Wikidata | 607 | Vici.org |
| Livius | 164 | Vici.org |
| DARE | 148 | Vici.org |

How the links were checked:
- **Pleiades' own citations** are authoritative where they exist. They confirmed 1,797 links, replaced 39 Vici links (for example, Constantinopolis had pointed to Byzantium) and added 454 more.
- **Matches by name and distance** were used only for places Pleiades doesn't cite. Where Pleiades also cites a place, the match agrees with Pleiades' citation every time: 107 of 107.
- **Uncertain matches**, 153 of them, were judged one by one, and each accepted match was re-checked by an independent skeptic, who upheld 151 of 152.
- **The 41 places where OmnesViae and Pleiades disagreed by 25 km or more** were resolved the same way. Where Pleiades' location proved better, the OpenStreetMap view uses it.
- **New coordinates:** 228 places that had no coordinates in OmnesViae now get them from Pleiades.

The real-world location rating gains a top level, *precise*, for when OmnesViae and a precisely located Pleiades place agree within 5 km.

## Sources and licences

- **Scan:** Konrad Miller, *Castori Romanorum Cosmographi Tabula quae dicitur Peutingeriana* (Ravensburg, 1887). Public domain.
- **Places and roads:** [OmnesViae](https://omnesviae.org) by René Voorburg, based on Richard J. A. Talbert, *Rome's World: The Peutinger Map Reconsidered* (Cambridge University Press, 2010). `places.json` is derived from the OmnesViae dataset, which is MIT-licensed; see [LICENSE-omnesviae.txt](LICENSE-omnesviae.txt).
- **Identifiers:** [Vici.org](https://vici.org) linked data (CC0 metadata, via its SPARQL endpoint) and the [Pleiades](https://pleiades.stoa.org) data dumps (CC BY). Vici's descriptions are CC BY-SA, so they are linked, not copied.
- **Grid squares:** the segment-grid references (e.g. Roma = 4B5) come from the online database accompanying *Rome's World*, consulted via the Internet Archive.
- **Modern map:** © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.
- **Map library:** [Leaflet](https://leafletjs.com).

## Files

- `index.html`: the app.
- `places.json`: places (Table spelling `n`, modern name `m`, real-world coordinates `ll`, position on the scan `xy`, how it was placed `c`, Talbert grid square `g`, confidence score `q` with reasons `qr`, real-world location rating `lq`, identifiers `ids` with Vici `v`, Pleiades `p`, Wikidata `w`, Livius `l` and DARE `d`, Pleiades name `pt`, Vici type `vt`) and roads (pairs of places with distances).
- `strip_00.jpg` to `strip_12.jpg`: the scan, cut into 2048-px-wide strips.
- `tools/`: the extraction scripts: road tracing (`trace.py`), OCR (`ocr.swift`), grid model (`grid.py`), grid-constrained matching (`ocrmatch2.py`), review crops and contact sheets (`render_review.py`, `render_points.py`, `zoom.py`), applying the review (`apply_review.py`, `apply_m13.py`), confidence scoring (`confidence.py`), linking identifiers (`vici_join.py`, `pleiades_match.py`, `merge_ids.py`) and building `places.json` (`build_places.py`). They're written for a local working folder and need path changes before they can be re-run.
