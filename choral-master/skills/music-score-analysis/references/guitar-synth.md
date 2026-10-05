# Electric Guitar Synthesis

## Guitar Note Synthesis

```python
def synthesize_guitar_note(freq_hz, duration_sec, velocity=0.8, sr=44100):
    # Pick attack noise (broad spectrum)
    # Even-harmonic string resonance (electric guitar)
    # Amp envelope: fast attack (2ms), medium decay (100ms), sustain (60%), fast release (200ms)
    return y / max(abs(y)) * 0.9
```

## Guitar Accompaniment

```python
def generate_guitar_accompaniment(notes, tempo_factor=1.0, sr=44100):
    # Same chord detection as piano
    # Bass notes (octave below melody)
    # Chord tones plucked softly every 4 melody notes
    return mix_audio_tracks([notes_to_audio_guitar(bass_notes),
                             notes_to_audio_guitar(chord_notes)])
```

## Key Difference from Piano

- Guitar: even harmonics dominant, fast attack noise (pick), string resonance decay
- Piano: all harmonics, hammer noise, exponential decay
- Both: ADSR envelope, velocity sensitivity