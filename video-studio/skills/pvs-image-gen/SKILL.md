---
name: pvs-image-gen
description: Génère images réalistes cohérentes avec ombres et lumière.
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [image, generation, realistic, GPT-Image, consistency]
    related_skills: [pro-video-storyteller, pvs-art-direction, pvs-animation]
---

# Agent Génération d'Images

## When to Use
- Phase asset generation : créer les visuels à partir de la shot list.
- Besoin de personnages, décors, accessoires avec cohérence.
- `Don't use for: animation, montage, voix`.

## Prerequisites
- `OPENAI_API_KEY` configuré pour GPT Image.
- Style Bible + Character Bible de pvs-art-direction.
- Photo référence personnage (optionnel, pour cohérence visage).

## Output
- Images versionnées par scène et plan : `assets/images/<project_id>/scene_<id>_<plan>_v<num>.png`
- Manifest d'assets avec hash SHA-256 pour traçabilité.

## Procedure
1. Lire la Scene List + Shot List + Style Bible.
2. Pour chaque plan, construire le prompt GPT Image :
   - Description visuelle détaillée (sujet, décor, action).
   - Lumière : source, direction, température couleur.
   - Ombres : dures/douces, longueur, direction (cohérente avec Style Bible).
   - Caméra : angle, distance, profondeur de champ.
   - Style : photoréaliste, cinématique, HDR.
3. Si photo référence : inclure comme image de référence + décrire le personnage exactement.
4. Générer l'image, vérifier cohérence visuelle avec la bible.
5. Si échec ou artefact : retry avec prompt ajusté (max 3 attempts).
6. Sauvegarder avec versionnage, enregistrer dans Asset Registry.

## Pitfalls
- GPT Image ne respecte pas toujours les consignes d'ombre → préciser "shadow direction: [direction], intensity: [soft/hard]".
- Visage incohérent sans photo → utiliser la description Character Bible de manière répétée dans chaque prompt.
- Format d'image incorrect → forcer le ratio (16:9, 9:16) dans le prompt.

## Verification
- Chaque image : ombre présente et direction cohérente avec Style Bible.
- Personnage : apparence identique d'une image à l'autre (mêmes traits, vêtements).
- Résolution ≥ 1920x1080 pour production 1080p.
- Hash SHA-256 enregistré dans Asset Registry.
