---
name: pvs-music-sfx
description: Musique originale, ambiances, bruitages, Foley et mixage.
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [music, sfx, sound-design, elevenlabs, audio]
    related_skills: [pro-video-storyteller, pvs-video-edit]
---

# Agent Musique & Sound Design

## When to Use
- Phase audio : créer la musique de fond, ambiances, bruitages, Foley.
- Besoin de bande-son originale synchronisée avec la vidéo.
- `Don't use for: montage vidéo ou génération d'images`.

## Prerequisites
- `ELEVENLABS_API_KEY` (Sound Effects) + `OPENAI_API_KEY` (optionnel, musique IA).
- Scene List : chaque scène a une ambiance et un mood définis.

## Output
- Piste musique : `assets/audio/<project_id>/music_<mood>_v<num>.mp3`
- Pistes SFX : `assets/audio/<project_id>/sfx_<scene>_<type>_v<num>.mp3`
- Mix final : voix + musique + SFX équilibrés.

## Procedure
1. Analyser la Scene List : identifier mood/ambiance par scène.
2. Générer la musique : style adapté au genre (cinématique, techno, ambient, etc.), boucleable.
3. Générer les SFX : ambiances (vent, ville, nature), impacts, Foley, transitions.
4. Synchroniser : SFX sur les actions visuelles, musique sur le rythme narratif.
5. Mixage : voix -6dB (intelligible), musique -18dB (fond), SFX -12dB (accents).
6. Vérifier : voix claire, musique non envahissante, SFS sync.

## Pitfalls
- Musique trop forte → couper pendant les dialogues.
- SFX non sync → vérifier les timecodes.
- Droits d'auteur → utiliser uniquement des sources autorisées/générées.

## Verification
- Mixage équilibré : voix intelligible, musique en soutien.
- SFX synchronisés avec les actions visuelles.
- Pas de clipping audio (vérifier les niveaux).
