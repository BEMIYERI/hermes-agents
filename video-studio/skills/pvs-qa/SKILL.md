---
name: pvs-qa
description: "Contrôle qualité vidéo : scénario, visuels, audio."
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [qa, quality-control, validation, compliance, review]
    related_skills: [pro-video-storyteller, pvs-video-edit]
---

# Agent Conformité / Expert Vidéo QA

## When to Use
- Fin de chaque phase : valider les livrables avant de passer à la suivante.
- Contrôle final avant delivery : QA exhaustif.
- `Don't use pour: générer du contenu → contrôler le contenu existant`.

## Input
- Livrables de chaque agent (vidéo, audio, images, sous-titres, script).
- Project Bible : critères de référence.
- Brief utilisateur : attentes originales.

## Output
- Rapport QA : score par catégorie (0-100), défauts identifiés, corrections requises.
- Verdict : PASS / FAIL + liste de corrections.

## Categories de contrôle
1. **Scénario** : cohérence narrative, hook, CTA, durée.
2. **Visuels** : continuité visage/ombres/lumière, résolution, artefacts.
3. **Animation** : fluidité, artefacts, mouvement naturel.
4. **Audio** : voix intelligible, mixage équilibré, sync.
5. **Sous-titres** : sync, lisibilité, fautes, longueur.
6. **Langue** : terminologie, ton, traduction fidèle.
7. **Droits** : licences assets, autorisation personnes.
8. **Technique** : codec, résolution, FPS, intégrité fichier.

## Procedure
1. Examiner chaque catégorie avec les critères de la Project Bible.
2. Scorer chaque catégorie 0-100.
3. Identifier les défauts critiques (bloquant) et mineurs (cosmétique).
4. Si score < 80 ou défauts critiques → FAIL + liste corrections.
5. Si score ≥ 80 et pas de défauts critiques → PASS.
6. Journaliser le rapport dans le dossier projet.

## Pitfalls
- QA trop indulgent → être exigeant, rechercher activement les défauts.
- Oublier la continuité → comparer visuellement scène par scène.
- Ne pas vérifier les droits → toujours contrôler les licences.

## Verification
- Score par catégorie documenté.
- Défauts critiques listés avec correction requise.
- Verdict cohérent avec les scores.
- Si FAIL : liste de corrections précise envoyée à l'agent concerné.
