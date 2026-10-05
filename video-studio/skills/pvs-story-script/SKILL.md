---
name: pvs-story-script
description: Transforme titre ou idée en histoire, narration, dialogues.
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [story, script, writing, narration]
    related_skills: [pro-video-storyteller]
---

# Agent Story & Script

## When to Use
- L'utilisateur fournit un titre, une idée ou un concept → développer l'histoire.
- Besoin de synopsis, structure narrative, dialogues, hook, découpage scène.
- `Don't use for: montage, génération d'images ou audio`.

## Input
- Brief utilisateur (titre, idée, histoire, script brut).
- Project Bible (si reprise) : genre, public, ton, durée cible.

## Output (contrat inter-agents)
```
project_id, scene_id="SCRIPT", agent_id="pvs-story-script",
status=done,
output_refs: {synopsis, structure, scenes[{id, description, duration_sec, hook, cta}],
               dialogues, narration_text}
```

## Procedure
1. Lire le brief, détecter langue, genre, public cible, durée souhaitée.
2. Développer synopsis (2-3 phrases) + structure (intro, développement, climax, conclusion).
3. Écrire hook (3-5 sec d'accroche) et CTA éventuelle.
4. Découper en scènes : chaque scène = ID unique, description visuelle, durée cible (5-15 sec).
5. Rédiger dialogues et narration pour chaque scène.
6. Valider : total durée ≈ cible, chaque scène a une action visuelle claire.
7. Retourner au orchestrateur avec la Scene List prête pour pre-production.

## Pitfalls
- Scènes trop longues (>15s) → découper.
- Dialogues non adaptés au format vidéo → préférer narration courte + visuel.
- Hook faible → réécrire avant de passer à l'étape suivante.

## Verification
- Nombre de scènes × durée ≈ durée cible ±10%.
- Chaque scène a : description visuelle, durée, hook/CTA si applicable.
- Script lu à voix haute : rythme naturel, pas de phrases trop longues.
