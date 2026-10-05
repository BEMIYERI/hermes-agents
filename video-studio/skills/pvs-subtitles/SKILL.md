---
name: pvs-subtitles
description: "Sous-titres : transcription, sync, style lisible."
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [subtitles, captions, transcription, srt, vtt]
    related_skills: [pro-video-storyteller, pvs-voice-direct]
---

# Agent Sous-titres

## When to Use
- Après génération audio final : créer les sous-titres synchronisés.
- Besoin de transcription, segmentation, style, contrôle lisibilité.
- `Don't use for: génération d'images ou d'animation`.

## Prerequisites
- `OPENAI_API_KEY` pour transcription (modèle Whisper).
- Audio final (voix mixée) de pvs-video-edit.
- Règles de style de la Project Bible.

## Output
- Fichier SRT : `exports/<project_id>.srt`.
- Fichier VTT : `exports/<project_id>.vtt` (si demandé).
- Version incrustée : optionnel, demandée explicitement.

## Procedure
1. Transcrire l'audio final avec Whisper → texte brut + timecodes.
2. Segmenter : chaque sous-titre = 1-2 phrases, max 42 car/ligne, 2 lignes max.
3. Synchroniser : timecodes précis (±0.5s), duration 1-6 sec par sous-titre.
4. Corriger : ponctuation, orthographe, segmentation naturelle.
5. Appliquer style : police lisible (Sans-serif), taille ≥24pt, fond semi-transparent.
6. Vérifier : aucun chevauchement avec éléments visuels importants.
7. Générer SRT + VTT, enregistrer dans Asset Registry.

## Pitfalls
- Timecodes décalés → revérifier la synchro audio/vidéo.
- Sous-titres trop longs → couper en 2, jamais plus de 2 lignes.
- Ponctuation absente → ajouter pour la lisibilité.
- Chevauchement avec UI/texte → repositionner ou ajuster timing.

## Verification
- Lecture synchronisée : texte apparaît au bon moment, disparaît naturellement.
- Aucun sous-titre > 2 lignes ou > 42 car./ligne.
- Pas de fautes d'orthographe critiques.
- Fichiers SRT/VTT valides (parseables).
