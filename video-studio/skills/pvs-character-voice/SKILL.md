---
name: pvs-character-voice
description: Génère voix personnages et narration avec ElevenLabs.
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [voice, tts, elevenlabs, characters, narration]
    related_skills: [pro-video-storyteller, pvs-voice-direct]
---

# Agent Parole des Personnages

## When to Use
- Phase audio : générer les voix à partir de la Voice Direction Sheet.
- Besoin de narration et dialogues avec émotion, multilingue.
- `Don't use for: montage, génération d'images`.

## Prerequisites
- `ELEVENLABS_API_KEY` configuré.
- Voice Direction Sheet de pvs-voice-direct.
- Voix clonées ou sélectionnées (vérifier autorisation si personne réelle).

## Output
- Fichiers audio voix : `assets/audio/<project_id>/scene_<id>_<locuteur>_v<num>.mp3`
- Audio mix final (voix seule, prêt pour le montage).

## Procedure
1. Lire la Voice Direction Sheet + Character Bible (attribution voix).
2. Pour chaque réplique, sélectionner la voix ElevenLabs appropriée.
3. Générer l'audio avec les paramètres : stabilité 0.5, clarté 0.75, style émotion marqué.
4. Si clonage vocal : vérifier autorisation explicite du propriétaire.
5. Vérifier : audio clair, émotion conforme, prononciation correcte.
6. Si erreur : retry avec paramètres ajustés (max 3 attempts).
7. Enregistrer dans Asset Registry.

## Pitfalls
- Voix non disponible → fallback sur voix similaire + note.
- Clonage sans autorisation → STOP, demander validation humaine.
- Audio trop court/long → ajuster le texte ou la vitesse de lecture.
- Prononciation incorrecte → ajouter phonétique dans le prompt.

## Verification
- Chaque réplique a un fichier audio correspondant.
- Audio jouable : pas de silence excessif, pas de distorsion.
- Émotion perceptible et cohérente avec la Voice Direction Sheet.
