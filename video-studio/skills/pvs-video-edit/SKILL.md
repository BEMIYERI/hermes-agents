---
name: pvs-video-edit
description: "Montage vidéo pro : plans, transitions, export."
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [editing, montage, ffmpeg, timeline, export]
    related_skills: [pro-video-storyteller, pvs-animation]
---

# Agent Montage Vidéo

## When to Use
- Phase post-production : assembler les clips animés en vidéo finale.
- Besoin de transitions, rythme, effets, titre, export.
- `Don't use pour: génération d'images ou d'animation`.

## Prerequisites
- FFmpeg installé et dans PATH.
- Clips animés de pvs-animation + audio (voix, musique, SFX) de pvs-music-sfx.
- Sous-titres de pvs-subtitles (optionnel, incrustation).

## Output
- Vidéo master : `exports/<project_id>_master.mp4` (H.264/H.265, AAC).
- Variantes sociaux : `exports/<project_id>_916.mp4`, `_11.mp4` si demandés.
- Rapport de montage : timeline, durées, transitions utilisées.

## Procedure
1. Recevoir les clips animés triés par ordre de scène + audio + sous-titres.
2. Construire la timeline : concaténation des clips avec durées exactes.
3. Appliquer transitions : coupure franche (habituel), fade in/out (intro/outro), crossfade (transitions narratives).
4. Superposer voix, musique et SFX selon l'Audio Bible.
5. Incruster sous-titres si demandé (position non chevauchante).
6. Color management : correction couleur cohérente entre clips.
7. Normalisation audio : voix -6dB, musique -18dB, SFX -12dB.
8. Exporter master (H.264, 1080p, 24/30fps, AAC 192kbps).
9. Exporter variantes si demandées (9:16 vertical, 1:1 carré).
10. Vérifier intégrité du fichier (FFprobe).

## Pitfalls
- Transition abusive → limiter à 2-3 transitions par vidéo, servir le récit.
- Audio désynchronisé → vérifier timecodes avant montage.
- Sous-titres chevauchant l'action → ajuster position/timing.
- FPS inconsistant → convertir tous les clips au même FPS avant montage.

## Verification
- FFprobe : fichier valide, codec, résolution, FPS, durée conformes.
- Lecture test : transitions fluides, audio sync, pas de coupure audible.
- Taille fichier raisonnable (<500MB pour 5 min en 1080p).
