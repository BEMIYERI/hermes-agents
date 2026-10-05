---
name: pro-video-storyteller
description: Orchestrateur multi-agents autonome de production vidéo pro.
version: 1.0.0
author: Nanga (nanga), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [video, multi-agent, orchestrator, production, cinematic]
    related_skills: []
---

# PRO VIDEO STORYTELLER — Orchestrateur Principal

## When to Use
- L'utilisateur fournit un titre, une idée, une histoire, un script ou des médias → démarre le workflow complet.
- Besoin de coordonner les 12 sous-agents spécialisés avec mémoire de projet et QA.
- `Don't use for: tâches ponctuelles qui ne nécessitent pas l'ensemble du pipeline`.

## Prerequisites
- **Free stack (no API keys, no accounts):** FFmpeg, Python 3.10+, numpy, scipy, Pillow, moviepy, edge-tts, openai-whisper, diffusers (SD v1.5 local, 4GB).
- **Optional APIs:** `HF_TOKEN` (HF Inference API), `OPENAI_API_KEY` (GPT Image + STT), `ELEVENLABS_API_KEY` (TTS), `RUNWAY_API_KEY` (I2V) — upgrade path only.
- HF_TOKEN peut être passé en variable d'environnement OU placé dans `~/.huggingface/token`.
- FFmpeg dans PATH.
- Stockage : `~/pro-video-studio/projects/<project_id>/` ou `C:/Users/<user>/pro-video-studio/`.

## How to Run
Lancer par `skill_use` avec le prompt de brief. L'orchestrateur lit le brief, crée le Project ID, puis délègue séquentiellement aux agents selon la phase.

## Workflow (12 étapes)
1. **Intake & Brief** — lire l'entrée, détecter langue, créer Project ID, initialiser Project Bible.
2. **Story & Script** (pvs-story-script) — synopsis, structure, dialogues, découpage scène.
3. **Pre-production** (pvs-art-direction) — Character/World/Style Bible, shot list, storyboard.
4. **Asset Generation** (pvs-image-gen) — personnages, décors, plans avec cohérence.
5. **Animation** (pvs-animation) — image-to-video, mouvements naturels.
6. **Voice & Language** (pvs-character-voice + pvs-languages) — voix, traduction FR↔EN.
7. **Music & SFX** (pvs-music-sfx) — musique originale, ambiances, bruitages.
8. **Subtitles** (pvs-subtitles) — transcription, sync, style.
9. **Editing** (pvs-video-edit) — timeline, transitions, mixage, export.
10. **Expert QA** (pvs-qa) — contrôle continuité, qualité, conformité.
11. **Repair Loop** — si QA échoue, renvoyer aux agents concernés, recontrôler (max 3 retries).
12. **Final Delivery** (pvs-packaging) — master + variantes, manifest, rapport QA.

## Project Bible (persistante)
- Character Bible : fiches personnages (apparence, traits, voix, évolution).
- World Bible : lieu, époque, météo, ambiance.
- Style Bible : palette, lumière, ombres, caméra, composition.
- Scene List : ID, durée cible, statut, version du prompt.
- Audio Bible : pistes voix, musique, SFX par scène.
- Subtitle Rules : style, position, longueur ligne.
- Asset Registry : tous les assets avec IDs et droits.
- Prompt Registry : prompts versionnés par scène.
- Versions : historique complet, jamais d'écrasement.
- Quality Gates : seuils par catégorie.

## Contrat Inter-Agents
Chaque message d'agent contient : `project_id, scene_id, agent_id, input_refs, output_refs, status, quality_score, warnings, errors, version, estimated_cost, next_action`.
Les agents ne modifient jamais le travail d'un autre sans passer par l'orchestrateur.

## Human Gates
- Brief ambigu → demander clarification.
- Photo personne réelle → autorisation explicite avant utilisation.
- Dépense > budget → confirmation.
- Scène sensible → validation.
- Publication automatique → désactivée (AUTO_PUBLISH=disabled).

## Constraints
- Cohérence des visages, ombres, lumière d'une scène à l'autre.
- Chaque image : source lumineuse identifiable, ombres crédibles.
- Transitions : servir le récit, pas d'effets gratuits.
- Sous-titres : lisibles, non chevauchants.
- Voix intelligibles, musique en dessous.
- Versionnement : jamais d'écrasement de master validé.
- Droits : respecter les licences des assets externes.

## User Preferences (Nanga)
- Format vertical 9:16 (1080×1920) par défaut — style WhatsApp stories.
- Audio stéréo AAC obligatoire (pas de mono).
- 30fps minimum.
- Durée longue (viser 100s+ avec plus de scènes).
- Pas de création de compte — free tools only en priorité.
- Français langue de travail.

## Pitfalls
- **Frames noires aux coupures concat** : toujours ré-encoder avec `-c:v libx264 -crf 23 -preset fast -pix_fmt yuv420p -movflags +faststart` après concat, jamais de copie directe. Vérifier avec ffprobe.
- **Audio mono par défaut** : ajouter `-ac 2` systématiquement. Vérifier le master avec ffprobe audio stream.
- **Pillow brightness trop sombre** : palettes vives (#7b4dff, #ff6b9d, #ffd700) + vignette subtile (glow center) + lens flare. Toujours vérifier mean pixel value (cible ~85-95).
- **API free tier bloquante** : Pollinations 402, HF DNS timeout, DeepAI 401, Craiyon 403. SD v1.5 local = 4GB, téléchargement lent (~1.4MB/s). DNS HF (`api-inferencing.huggingface.co`) bloqué au niveau réseau — ni Google DNS (8.8.8.8) ni Cloudflare (1.1.1.1) ne résolvent. Vérifier avec `nslookup api-inference.huggingface.co 8.8.8.8` avant de chercher un token. Ne pas bloquer le pipeline dessus — Pillow reste le fallback fiable.
- **GPT Image ne respecte pas toujours les consignes d'ombre** → préciser "shadow direction: [direction], intensity: [soft/hard]".
- **Visage incohérent sans photo** → utiliser la description Character Bible de manière répétée dans chaque prompt.
- **Format d'image incorrect** → forcer le ratio (16:9, 9:16) dans le prompt.
- **Cartoon Pillow fallback** : quand AI image gen indisponible, utiliser silhouettes cartoon (ellipse visage + rounded_rectangle corps) + palettes vives + glow center + lens flare + particles. Mean brightness cible ~75-90.

## Failure Behavior
- Journaliser : Agent ID, Scene ID, Asset ID, étape, outil, message.
- Classifier : contenu, cohérence, génération, API, audio, montage, sous-titres, stockage, qualité.
- Retry automatique (max 3) avec stratégie différente.
- Fallback outil si disponible.
- Régénérer uniquement l'asset fautif.
- Après échec retries → intervention humaine avec diagnostic.

## Stop Conditions
- Entrées essentielles absentes et non déductibles.
- Génération répétée non conforme.
- Outils indispensables indisponibles.
- Budget atteint.
- Action externe non autorisée.

## Success Criteria
- Vidéo correspond au brief, narration compréhensible.
- Personnages cohérents visuellement.
- Images réalistes avec ombres/lumière crédibles.
- Animation fluide, artefacts mineurs uniquement.
- Transitions professionnelles, rythme soutenu.
- Voix naturelles, bien attribuées.
- Audio mixé correctement.
- Sous-titres synchronés, lisibles.
- Langue respectée, traduction fidèle.
- Fichier final passe contrôles techniques.

## Evidence (livrables)
- Vidéo master + variantes.
- Manifest JSON (scènes, assets, versions, outils, modèles).
- Script final + storyboard.
- Project Bible complète.
- Piste audio, voix, musique, SFX.
- Fichier sous-titres (SRT/VTT).
- Rapport QA avec scores.
- Journal erreurs/retries.
- Rapport provenance assets.
