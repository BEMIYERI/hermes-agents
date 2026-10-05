# Python 3.14 Audio Compatibility

## The Problem

Python 3.13+ removed `audioop` module. On Windows with Hermes Python 3.14:
- `pydub` depends on `audioop` (or `pyaudioop` shim which is also absent)
- `simpleaudio` C extension fails to build (needs MSVC 14.0)
- `pygame` wheel build fails on this Python version

**Result**: `pip install pydub simpleaudio pygame` all fail or install broken.

## The Working Solution

Use numpy + wave + winsound for all audio needs:

```python
import numpy as np
import wave, struct
import winsound

# Generate WAV from note events
sr = 44100
audio = np.zeros(total_samples, dtype=np.float64)
# ... fill with sine/harmonic synthesis ...
audio = np.clip(audio, -1, 1)
int_audio = (audio * 32767).astype(np.int16)
with wave.open(path, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    wf.writeframes(int_audio.tobytes())

# Play
winsound.PlaySound(path, winsound.SND_ASYNC | winsound.SND_FILENAME)
winsound.PlaySound(None, winsound.SND_ASYNC)  # stop
```

## Piano Synthesis (Enhanced — 8 harmonics + accompaniment)

```python
def synthesize_note(freq_hz, duration_sec, velocity=0.8, sr=44100):
    n_samples = int(sr * duration_sec) + sr
    t = np.linspace(0, duration_sec, n_samples, False)
    y = np.zeros(n_samples, dtype=np.float64)
    # 8 harmonics with inharmonicity
    harmonics = [
        (1.0, 1.0), (2.0, 0.5), (3.0, 0.25), (4.0, 0.15),
        (5.0, 0.1), (6.0, 0.07), (7.0, 0.04), (8.0, 0.02),
    ]
    for i, (mult, amp) in enumerate(harmonics):
        stretch = 1.0 + 0.0001 * (i ** 2) * mult
        y += amp * np.sin(2 * np.pi * freq_hz * stretch * t * mult)
    # Hammer noise at attack
    n_hammer = int(0.003 * sr)
    if n_hammer > 0 and n_hammer <= n_samples:
        hammer_noise = np.random.normal(0, 1, n_hammer)
        hammer_env = np.exp(-np.arange(n_hammer) / (sr * 0.001))
        y[:n_hammer] += hammer_noise * hammer_env * velocity * 0.3
    # ADSR + exponential decay
    # ...
    return y / max(abs(y)) * 0.85
```

## Piano Accompaniment (bass + chords from melody)

```python
def generate_accompaniment(notes, tempo_factor=1.0, sr=44100):
    # Detect chord from melody pitch classes
    pitch_classes = set(n['pitch_midi'] % 12 for n in notes if n.get('pitch_midi'))
    root = min(pitch_classes)
    has_major_third = (root + 4) % 12 in pitch_classes
    has_minor_third = (root + 3) % 12 in pitch_classes
    chord_tones = [root]
    if has_major_third: chord_tones.append(root + 4)
    elif has_minor_third: chord_tones.append(root + 3)
    else: chord_tones.append(root + 4)
    chord_tones.append(root + 7)
    # Bass notes (octave below melody)
    bass_notes = [{'pitch_midi': n['pitch_midi'] - 12,
                   'duration_beats': n.get('duration_beats', 1) * 0.5,
                   'velocity': n.get('velocity', 0.7) * 0.5}
                  for n in notes]
    # Chord notes (soft, every 4 melody notes)
    chord_notes = []
    for i, n in enumerate(notes):
        if i % 4 == 0:
            for tone in chord_tones:
                chord_notes.append({'pitch_midi': tone + 12,
                                    'duration_beats': n.get('duration_beats', 1) * 2,
                                    'velocity': n.get('velocity', 0.7) * 0.3})
    return mix_audio_tracks([notes_to_audio(bass_notes), notes_to_audio(chord_notes)])
```

## MIDI Note → Frequency

```python
def midi_to_freq(midi_note):
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
```

## Key Takeaway

Do NOT waste time trying to install pydub/simpleaudio/pygame on Python 3.14 — they will fail. numpy+wave+winsound is the reliable path for WAV generation and playback on this platform.

## Drums Synthesis (realistic drum accompaniment)

`synthesize_drums(notes, tempo, duration_sec)` generates kick (beats 1,3), snare (beats 2,4), hi-hat (8th notes), crash (every 4 bars). Pattern-based synthesis — no samples needed. Apply volume multiplier after generation: `drum_audio * self.vol_drums`.