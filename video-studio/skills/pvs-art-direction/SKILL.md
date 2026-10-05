---
name: pvs-art-direction
description: "Direction artistique : lumière, ombres, caméra."
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [art-direction, style, lighting, cinematography]
    related_skills: [pro-video-storyteller, pvs-image-gen]
---

# Agent Direction Artistique & Réalisme

## When to Use
- Phase pre-production : définir le style visuel avant génération d'images.
- Besoin de cohérence lumineuse et de continuité visuelle.
- `Don't use for: générer des images directement → utiliser pvs-image-gen`.

## Input
- Script (Scene List de pvs-story-script).
- Contexte projet : genre, public, plateforme, format.
- Photo référence personnage (si fournie par l'utilisateur).

## Output
- Character Bible : apparence personnage principal(s), vêtements, traits.
- World Bible : lieux, époque, météo, heure, ambiance.
- Style Bible : palette couleurs, direction lumière, type d'ombres, caméra, composition.
- Shot List : plan par plan avec angle, mouvement, profondeur de champ.
- Storyboard textuel : description visuelle scène par scène.

## Procedure
1. Analyser le script : identifier lieux, époques, humeurs, transitions.
2. Définir Character Bible : physique, vêtements, accessoires, expressions typiques.
3. Définir World Bible : macro-lieu, micro-lieux, heure, météo, saison.
4. Définir Style Bible : palette (3-5 couleurs), direction lumière (key/fill/rim),
   type d'ombres (douces/dures selon mood), angle caméra, composition (rule of thirds).
5. Créer Shot List : pour chaque scène → plan(s) avec angle, mouvement caméra, sujet, fond.
6. Rédiger Storyboard textuel : description visuelle par plan, indication de mouvement.
7. Vérifier continuité : même personnage = même apparence partout, même lumière pour même lieu.

## Pitfalls
- Ombres incohérentes entre scènes → fixer direction lumière dans Style Bible.
- Personnage qui change d'apparence → figer Character Bible dès le départ.
- Plans trop similaires → varier angles et distances.

## Verification
- Character Bible : un fichier, tous les détails figés.
- Shot List : un plan par scène minimum, angle+succion distincts.
- Continuité vérifiée : même lieu = même heure/météo/lumière.
