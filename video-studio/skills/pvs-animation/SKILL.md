---
name: pvs-animation
description: Anime images en vidéos fluides, cinématique.
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [animation, image-to-video, runway, motion, cinematic]
    related_skills: [pro-video-storyteller, pvs-image-gen]
---

# Agent Animation / Image-to-Video

## When to Use
- Après génération des images : transformer les plans statiques en clips animés.
- Besoin de mouvement caméra, parallax, profondeur, mouvement naturel.
- `Don't use for: génération d'images, montage final`.

## Prerequisites
- `RUNWAY_API_KEY` configuré (Image-to-Video).
- Images générées par pvs-image-gen.
- Fallback : autre moteur I2V compatible (Pika, Kling, Minimax).

## Output
- Clips vidéo animés : `assets/video/<project_id>/scene_<id>_<plan>_v<num>.mp4`
- Métadonnées : durée, FPS, résolution, mouvements appliqués.

## Procedure
1. Lire les images versionnées + Shot List (mouvements souhaités par plan).
2. Pour chaque image, construire la requête I2V :
   - Image source.
   - Motion description : type de mouvement (zoom, pan, tilt, drift, rotate).
   - Durée cible du clip (3-10 sec).
   - Qualité : cinematic, haute fidélité.
3. Générer le clip vidéo.
4. Vérifier : fluidité, pas d'artefacts majeurs, mouvement cohérent avec l'image.
5. Si artefact critique : régénérer avec motion description ajustée (max 3 retries).
6. Enregistrer dans Asset Registry.

## Pitfalls
- Runway refuse parfois certains prompts → simplifier la motion description.
- Mouvement trop rapide/chaotique → réduire l'intensité du motion prompt.
- Résolution insuffisante → générer en résolution native, ne pas upscaler artificiellement.
- Clips trop courts pour le montage → ajuster la durée cible.

## Verification
- Clip lisible : pas de glitch majeur, de distorsion ou de flickering.
- Mouvement naturel : pas de saccades, vitesse cohérente.
- Durée conforme à la demande ±1 sec.
- Résolution identique à l'image source.
