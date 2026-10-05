---
name: pvs-packaging
description: "Packaging final : exports, miniature, manifest."
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [packaging, export, delivery, thumbnail, metadata]
    related_skills: [pro-video-storyteller, pvs-video-edit]
---

# Agent Packaging / Publication

## When to Use
- Phase finale : exporter la vidéo master et les variantes.
- Besoin de miniature, métadonnées, manifest de projet.
- `Don't use pour: génération de contenu ou montage intermédiaire`.

## Prerequisites
- Master vidéo validé par pvs-qa (PASS).
- Script final, Project Bible complète, rapport QA.

## Output
- Master : `exports/<project_id>_master.mp4` (H.264/H.265, AAC).
- Variantes : `exports/<project_id>_916.mp4`, `_11.mp4` si demandées.
- Miniature : `exports/<project_id>_thumbnail.png`.
- Métadonnées : `exports/<project_id>_metadata.json`.
- Manifest : `exports/<project_id>_manifest.json`.
- Archive projet : `exports/<project_id>_archive.zip`.

## Procedure
1. Recevoir master validé + tous les assets.
2. Générer les variantes de format (9:16 vertical, 1:1 carré) via FFmpeg.
3. Créer la miniature : frame la plus représentative + overlay titre.
4. Générer les métadonnées : titre, genre, durée, langue, plateforme, modèles utilisés.
5. Générer le manifest JSON : scènes, assets, versions, outils, paramètres.
6. Archive projet : scripts, prompts, images sources, assets validés, audio, manifest, rapport QA.
7. Vérifier : tous les fichiers existent et sont valides.

## Pitfalls
- Manifest incomplet → inclure tous les IDs et versions.
- Métadonnées manquantes → remplir tous les champs obligatoires.
- Archive corrompue → tester l'extraction avant livraison.

## Verification
- Tous les fichiers exportés existent et sont lisibles.
- Manifest JSON parseable et complet.
- Miniature lisible, titre visible.
- Archive extractible sans erreur.
