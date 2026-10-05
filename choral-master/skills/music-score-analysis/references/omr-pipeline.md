# OMR Pipeline: PDF/Image → MusicXML

## Architecture

```
PDF ──┐
      ├──→ pymupdf (fitz) ──→ PNG pages ──→ image_processor ──→ music21 Score
JPEG/PNG ────────────────────────────────────→ image_processor ──→ music21 Score
```

## Staff Line Detection (synthetic images only)

1. Binarize: pixels < threshold → 255 (white), else 0 (black) — inverts image so staff lines are white on black
2. Project: `np.sum(arr > 200, axis=1)` — bright pixels per row
3. Find rows with > 5% width bright
4. Group consecutive rows (gap ≤ 2px) into line groups
5. Group 5-line clusters into staff systems (max_gap=10px between groups)

## Note Head Detection

1. For each staff region, find bright pixels (note heads are white on black bg after inversion)
2. Cluster by column: `col_sums = np.sum(bright_mask, axis=0)`
3. For each cluster: x = center, y = center row → pitch from staff position
4. Duration estimate: note head size/shape heuristic

## Pitch Mapping

- Treble clef staff center line → E5 (MIDI 64)
- Bass clef staff center line → D3 (MIDI 47)
- Offset from staff center: `pitch = base_pitch - offset` (higher y = lower pitch)
- Clamp to valid MIDI range: 21–108

## REAL PHOTOS: OCR.space API (WORKING PATH)

Staff-line detection FAILS on real photos of handwritten scores. Use OCR.space API instead:

```python
# POST to https://api.ocr.space/parse/image
# -F file=@image.jpg -F language=eng -F apikey=helloworld -F isOverlayRequired=false
# Free tier: 3 requests/day, no signup needed
```

The API returns Galin-Paris-Chevé letter notation text. Parse with `_gpcheve_parse_line()`:
- Split line by `:` → tokens
- Skip numeric tokens (OCR noise)
- Letters d/r/m/f/s/l/t → MIDI (base_do=60, uppercase = +octave)
- `-` token → rest (pitch_midi=None)
- Each line = one voice (Soprano→0, Alto→1, Ténor→2, Basse→3)

## Galin-Paris-Chevé Notation

Letters d/r/m/f/s/l/t = Do/Ré/Mi/Fa/Sol/La/Si. Uppercase = higher octave. `:` separates notes. `-` = rest/longer note. Numbers in OCR output = ignore (noise). Each line = one voice (Soprano, Alto, Ténor, Basse). Multiple systems stacked vertically.

## Scientific Pitch Notation (SPN)

Format: `C4(60) D4(62) E4(64)` — pitch name + octave + MIDI in parens. Each line = one voice.

Parser: `_parse_spn_text()` extracts tokens matching `[A-G][#b]?\d+\(\d+\)`. Header lines like "Paroles" / "Pas de paroles" are ignored (no matching tokens).

**Fallback order in `any_to_score()`**: SPN → GPChevé → empty. If GPChevé returns ≤1 note but SPN returns ≥2, the image is SPN format, not GPChevé. Swap the fallback order to try SPN first.

## Limitations

- Synthetic test images with thin staff lines may not trigger 30% row threshold — use 5%
- Note heads that span multiple staff lines merge into one bright region — keep note width < staff spacing
- Real music scans work better than synthetic tests (cleaner contrast, proper staff spacing)
- OMR confidence is low for complex scores — flag uncertainty and ask human
- **Staff-line detection does NOT work on photos** — use OCR.space API for real images
- Ténor voice often returns 0 notes from photos (OCR misses the line)
- **SPN images**: OCR.space may return only 1 note if the text extraction is incomplete — check that all note tokens are present; if not, re-OCR with different preprocessing