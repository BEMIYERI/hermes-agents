# music21 API Quirks (v10.x)

## Removed/Changed Attributes

| Old | New | Context |
|---|---|---|
| `.flat` | `.recurse()` | Part objects — `.flat` doesn't exist in music21 10.x |
| `.partId` | `getattr(part, 'id', '')` | Part identifier attribute renamed |
| `isinstance(n, music21.duration.Duration)` | `isinstance(n, music21.note.Rest)` | Rest detection — Duration is not a Rest base class |

## Note Extraction Pattern

```python
# Correct — recurse through all nested streams
for n in score.parts[part_idx].recurse().notes:
    if isinstance(n, music21.chord.Chord):
        pitch_midi = n.pitches[0].midi
    elif hasattr(n, 'pitch') and n.pitch:
        pitch_midi = n.pitch.midi
```

## Voice Mapping

Name-based first, then range fallback:
1. Check `part.partName` / `part.partAbbreviation` for "soprano", "alto", "tenor", "bass"
2. If unnamed, analyze pitch range against VOICE_RANGES config
3. Treble-clef tenor parts → misidentified as Alto (range overlap). Flag confidence.

## Caching

Parse is slow (10–30s for large scores). Cache by SHA-256 hash of file content (16-char hex key). Check cache before parsing.

## Note Dict Format (for synth)

```python
{"pitch_midi": int, "duration_beats": float, "velocity": float 0-1, "lyrics": list}
```
Key names: `pitch_midi` (NOT `pitch`), `duration_beats` (NOT `duration`). These are what `notes_to_audio()` expects.