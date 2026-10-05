---
name: music-score-analysis
description: Build agents that parse choral music scores (SATB).
version: "1.0.0"
author: nanga
license: proprietary
tags: [music, audio, synthesis, SATB, choral]
related_skills: [autonomous-ai-agents, software-development]
---

## When to Use

Triggered when the user asks to build an agent that reads, parses, separates voices from, or synthesizes audio from music scores (chorale partitions, SATB choir scores, hymnals). Also applies when adding voice extraction, piano accompaniment, or interactive playback to an existing music analysis agent.

# Music Score Analysis Agent

Build agents that parse choral/music scores, separate SATB voices, generate piano accompaniment, and provide interactive playback.

## Standing Rules

1. **Parse with music21** — `music21.converter.parse()` handles MusicXML, MIDI, and more. Cache by file hash (SHA-256, 16-char hex) to avoid re-parsing.
2. **Voice separation order**: name-based mapping first (partName/partAbbreviation contains "soprano", "alto", "tenor", "bass"), then range inference as fallback using `VOICE_RANGES` config.
3. **Extract notes via `.recurse().notes`** — NOT `.flat.notes` (doesn't exist in music21 10.x).
4. **Part ID**: use `getattr(part, 'id', '')` — `part.partId` does not exist in music21 10.x.
5. **Rest detection**: `isinstance(n, music21.note.Rest)` — NOT `isinstance(n, music21.duration.Duration)`.
6. **Synthesize audio with numpy+wave+winsound** on Python 3.14+ — `audioop` removed, `pydub`/`simpleaudio` won't install. Additive synthesis: fundamental + 4 harmonics with decreasing amplitude, ADSR envelope per note.
7. **MIDI → frequency**: `440.0 * 2.0 ** ((midi_note - 69) / 12.0)`.
8. **Multi-agent architecture**: orchestrateur coordinates partition analyst + per-voice agents (Soprano/Alto/Ténor/Basse) + piano agent + audio renderer. Each voice agent has `extract(score)` → `validate()` pipeline.
9. **Never invent notes** — if OMR/confidence low, flag uncertainty and ask human. Signal `confidence < 0.8` as warning.
10. **GUI**: tkinter with file upload, voice checkboxes, mode radio buttons (voice/piano/both/all), tempo slider (50–150%), loop controls, PLAY/STOP, lyrics display panel. Voice checkboxes must call `_update_voice_selection()` which reads BooleanVar states into `self.current_voices`. Mode radio buttons must call `_update_mode()`. These are NOT automatic — bind explicit command callbacks. **Volume sliders** for piano/guitar/voice/metronome/drums (0–100%) with `_on_volume()` callback reading all sliders. **Auto-apply**: tempo/realism/volume sliders trigger `_apply_settings()` before playback. **Drums**: `synthesize_drums()` adds kick/snare/hi-hat/crash pattern; toggle via `drums_var.get()`.
11. **OMR for PDF/Image**: Use `omr/` module — pymupdf renders PDF pages to PNG, then image_processor detects staff lines + note heads → music21 Score. `any_to_score()` auto-dispatches by extension (.pdf→OMR, .jpg/.png→OMR, else music21). **BUT**: staff-line detection FAILS on real photos of handwritten scores. Working fallback: OCR.space API (free key `helloworld`) extracts letter notation from photos. Two formats supported: Galin-Paris-Chevé (d/r/m/f/s/l/t) and Scientific Pitch Notation (C4(60) D4(62)). Parser: split by `:`, map letters to MIDI (base_do=60), uppercase = +octave. SPN format is tried FIRST in `any_to_score()` fallback chain because it's more precise. This is the ONLY reliable path for photo uploads.
12. **Galin-Paris-Chevé notation**: Letters d/r/m/f/s/l/t = Do/Ré/Mi/Fa/Sol/La/Si. Uppercase = higher octave. `:` separates notes. `-` = rest/longer note. Numbers in OCR output = ignore (noise). Each line = one voice (Soprano, Alto, Ténor, Basse). Multiple systems stacked vertically.
12a. **Scientific Pitch Notation (SPN)**: Format `C4(60) D4(62)` — pitch name + octave + MIDI in parens. Extracted via OCR.space API then `_parse_spn_text()`. Each line = one voice. Use when GPChevé parser returns 0–1 notes (image has SPN format, not letter notation). SPN text may include header lines like "Paroles" / "Pas de paroles" — filter those out, extract only `NOTE(OCTAVE)` tokens.
13. **Piano accompaniment**: NOT single-note melody. `generate_accompaniment()` detects chord from melody pitch classes, generates bass line (octave -12) + chord tones (root+3/root+4+7) at reduced velocity. Mix voice + accompaniment with `mix_audio_tracks()`. This is what the user wants — "Le piano est fade" means add chords.
13a. **Electric guitar accompaniment**: `generate_guitar_accompaniment()` — pick noise attack + even-harmonic string resonance + amp envelope (fast attack, medium decay, sustain, fast release). Bass line + chord tones at reduced velocity. Toggle via `guitar_var.get()` in GUI; checkbox "🎸 Guitare électrique" replaces piano when checked, supplements when unchecked. **Apply volume multiplier** `acc_audio * self.vol_guitar` after generation.
13b. **Live realism**: Apply `apply_reverb(audio, mix=0.3)` + `humanize_notes(notes, velocity_variation=0.1, timing_variation=0.02)` before playback. Add slider "Réalisme live" (0–100%) to GUI; reverb mix = slider/200. Humanization adds ±10% velocity variation and ±2% early timing per note — makes synthesized audio sound played, not sequenced.
13c. **Metronome**: `generate_metronome(bpm, duration_sec)` produces click tracks (1000Hz downbeat + 2000Hz upbeat, exponential decay). Checkbox "⏱ Métronome" in GUI. Mix with final audio via `mix_audio_tracks()`. **Apply volume multiplier** `met_audio * self.vol_metronome` after generation.
13d. **Drums accompaniment**: `synthesize_drums(notes, tempo, duration_sec)` generates kick (beats 1,3), snare (beats 2,4), hi-hat (8th notes), crash (every 4 bars). Apply volume multiplier `drum_audio * self.vol_drums` after generation.
14. **Lyrics extraction**: MusicXML `lyrics` element → `n.lyrics` → `ly.text`. Extract in `base_agent.py` note dict as `note["lyrics"]` list. Display in GUI lyrics panel. If no lyrics found, show note names as fallback with message "Pas de paroles. Notes: ...".
15. **Score.metadata may be None**: Always check `if score.metadata is None: score.metadata = music21.metadata.Metadata()` before setting `.title`. music21's `stream.Score()` creates a Score with None metadata. **Also applies to partition_analyst.py**: `meta = self.score.metadata` can be None — guard with `getattr(meta, 'title', None)` or create empty fallback object before accessing attributes.
16. **GUI save button**: Add `_save_project()` method using `simpledialog.askstring()` for project name. Saves voice selection, mode, guitar toggle, tempo, loop settings via `orch.save_project(name, settings)`. Persists to JSON for later restore.
17. **GUI Builder**: Separate interface (`gui_builder.py`) for programming GUI layout — drag-and-drop widget palette (Label, Button, Checkbutton, Radiobutton, Entry, Text, Scale, Frame, Listbox), live property editor, auto-generates Python code, save/load layouts as JSON. Launch with `python main.py --builder`. See `references/guitar-synth.md` for guitar + piano synthesis details.

## Pitfalls

- **`.flat` attribute missing**: music21 10.x removed `.flat` from Part objects. Use `.recurse()` instead. Affects: `partition_analyst.py`, `voice_agents.py`, `piano_synth.py`.
- **SPN parser returns 1 note**: If `_parse_spn_image()` returns only 1 note from an image, the image likely contains GPChevé format, not SPN. Swap fallback order: try SPN first, then GPChevé. Check OCR output — if it contains `d/r/m/f/s/l/t` letters, use GPChevé parser; if it contains `NOTE(OCTAVE)` tokens like `C4(60)`, use SPN parser.
- **SPN text contains non-note lines**: Header text like "Paroles" or "Pas de paroles" appears in OCR output. Filter to only lines matching `[A-G][#b]?\d+\(\d+\)` pattern.
- **Voice range constants**: Soprano MIDI 65–88, Alto 55–79, Ténor 48–72, Basse 40–64. These are hardcoded in `config.py` and used by range-inference fallback.
- **`part.partId` → `getattr(part, 'id', '')`**: music21 10.x uses `.id`, not `.partId`.
- **Python 3.14 audioop removal**: `pydub` and `simpleaudio` depend on `audioop` (removed in 3.13+). On Windows with Hermes Python 3.14, these wheels fail to build (no C++ compiler). Solution: numpy+wave+winsound for WAV generation/playback. Do NOT waste time trying to install pydub/simpleaudio — it will fail.
- **Voice map ambiguity**: Treble-clef tenor parts parse as Alto by range. Flag confidence < 1.0 when range overlap > 50% between adjacent voices.
- **music21 parse slowness**: Large scores take 10–30s. Always cache by hash. Check cache before parsing.
- **MIDI note dict key**: use `"pitch_midi"` not `"pitch"` — the agent note_dict format uses `pitch_midi`.
- **Duration key**: use `"duration_beats"` not `"duration"` in note dicts for `notes_to_audio()`.
- **Volume may be None**: guard with `vel = getattr(n, 'volume', None); velocity = vel.velocity / 127.0 if vel and vel.velocity else 0.7`.
- **OMR staff detection threshold**: 1px staff lines on synthetic test images may not trigger 30% row-brightness threshold. Lower to 5% or detect by grouping consecutive bright rows. Real music scans work better.
- **Synthetic test images**: Create with Pillow — white background, black staff lines (5 horizontal lines, 10px spacing), black note heads (ellipses). Note heads must be narrower than staff spacing or they merge into one bright region.
- **`stream.Score().metadata` is None**: `stream.Score()` creates Score with `metadata=None`. Must initialize before setting `.title`: `if score.metadata is None: score.metadata = music21.metadata.Metadata()`.
- **Cache bug for images**: When `load_cache()` returns a hit, the old code returned early WITHOUT setting `self.score`, leaving it `None` → "Chargez d'abord une partition" error on play. Fix: only use cache for metadata on non-image files; always re-parse images (PDF/JPEG/PNG) because OMR must re-run.
- **`sr` undefined in GUI `_play`**: The `_play` method used `sr` (sample rate) which wasn't in scope. Fix: import `SAMPLE_RATE` from `config` and use it in `generate_metronome()` calls instead of `sr`.
- **`config_scrollregion` not a Canvas method**: Tkinter Canvas has no `config_scrollregion()`. Use `self.canvas.configure(scrollregion=self.canvas.bbox("all"))` instead.
- **GPChevé fallback blocks SPN**: In `any_to_score()`, the old fallback order tried GPChevé before SPN. GPChevé may return 1 note for SPN-format images, preventing SPN parser from running. Fix: try SPN first, then GPChevé. Check OCR output — if it contains `d/r/m/f/s/l/t` letters, use GPChevé parser; if it contains `NOTE(OCTAVE)` tokens like `C4(60)`, use SPN parser.
- **`partition_analyst.py` meta=None crash**: `self.score.metadata` can be None for files without metadata (e.g., some JPEG exports). Guard all attribute accesses with `getattr(meta, 'title', None)` or create an empty fallback object before accessing attributes.
- **Metronome tempo must track slider**: `generate_metronome(120, ...)` hardcodes 120 BPM. The tempo slider sets `tempo_factor` (0.5–1.5x). Pass `120 * tempo_factor` as the BPM argument, not `120`. Otherwise the metronome clicks at a different speed than the audio plays.
- **`dark_mask` undefined in `image_processor.py`**: `detect_note_heads` references `dark_mask` (line 149) which does not exist — the variable is `bright_mask`. Patch before running OMR on images, or OMR crashes with NameError.
- **vision_analyze 404 on local files**: The vision_analyze tool returns 404 for local file paths. Inspect images via Python+PIL or run the OMR pipeline directly via terminal instead of relying on vision_analyze.
- **OMR may detect fewer voices than expected**: Image OMR grouped 2 staves into Voice_0/Voice_1 — verify voice assignment against expected SATB before synthesizing; range overlap causes misassignment.