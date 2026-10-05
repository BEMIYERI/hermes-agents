---
name: pvs-voice-direct
description: "Direction jeu vocal : prononciation, rythme, émotion."
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [voice, direction, performance, pronunciation]
    related_skills: [pro-video-storyteller, pvs-character-voice]
---

# Agent Voix / Direction de Jeu

## When to Use
- Phase pré-audio : préparer les indications de jeu pour la génération vocale.
- Besoin de prononciation, rythme, émotion par personnage.
- `Don't use for: générer l'audio directement → utiliser pvs-character-voice`.

## Input
- Script (dialogues + narration de pvs-story-script).
- Character Bible : voix assignées à chaque personnage.
- Langue cible (FR/EN).

## Output
- Voice Direction Sheet : pour chaque réplique → personnage, ton, émotion, rythme, pauses.
- Notes de prononciation : mots difficiles, noms propres, termes techniques.

## Procedure
1. Analyser le script : identifier locuteur, émotion, intention de chaque réplique.
2. Assigner un ton à chaque personnage : narration = calme/professionnel, dialogue A = enthousiaste, dialogue B = sérieux, etc.
3. Indiquer le rythme : rapide (action), lent (émotion), normal (narration).
4. Marquer les pauses : [pause 0.5s], [pause 1s] aux endroits dramatiques.
5. Noter la prononciation : noms propres, jargon technique, termes étrangers.
6. Vérifier : chaque réplique a un locuteur assigné + ton + rythme.

## Pitfalls
- Tons confus entre personnages → différencier clairement (grave/aigu, lent/rapide).
- Rythme uniforme → varier selon l'émotion de la scène.
- Prononciation ignorée → vérifier les noms propres et termes techniques.

## Verification
- Voice Direction Sheet complète : chaque réplique a locuteur + ton + rythme + pauses.
- Prononciation notée pour tous les termes ambigus.
- Cohérence : même personnage = même ton dans toutes les scènes.
