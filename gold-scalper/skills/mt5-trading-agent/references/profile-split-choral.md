# Scinder un agent spec du profil default (recette validee 04/10, Windows)

Quand l'humain veut un profil dedie pour un agent spec dont la vie existe deja dans le
profil default (memoires/skills/projects) — ex. CHORAL MASTER:

1. `hermes profile create <nom>` — creer le squelette (ne JAMAIS `--clone` : le clone
   embarque TOUTES les memoires du default, y compris les autres projets -> identite melee).
2. Credentials herites sans re-login : copier `%LOCALAPPDATA%/hermes/auth.json` ->
   `profiles/<nom>/auth.json` (same machine/user = OK ; les tokens ne sortent jamais de la machine).
3. Modele : `hermes -p <nom> config set model.provider nous` puis `model.default <id>`
   (recopier les valeurs du default : `hermes profile list` affiche le modele actif).
4. Skills : recopier UNIQUEMENT les dossiers de skills lies au projet
   (`skills/<...>` -> `profiles/<nom>/skills/`).
5. Identite : ecrire `profiles/<nom>/SOUL.md` (persona, regles, atelier, langue)
   + `memories/MEMORY.md` + `memories/USER.md` extraits des entrees default QUI CONCERNENT
   CE PROJET uniquement (grep le mot-cle du projet dans memories/MEMORY.md et USER.md).
   write_file refuse d'ecraser SOUL.md sans lecture prealable -> read_file d'abord.
6. Ne PAS retirer les entrees du profil default sans accord explicite (le default continue
   de servir d'autres agents).
7. TEST D'IDENTITE obligatoire : `hermes -p <nom> chat -q "Qui es-tu... 3 lignes"` ;
   la reponse brute n'est pas toujours dans stdout (footer resume) -> la lire dans
   `profiles/<nom>/state.db`, table `messages` (role=assistant, session_id donne).
8. Bot Telegram dedie = etape HUMAINE : BotFather -> /newbot ; le token ne doit JAMAIS
   transiter par le chat — l'humain le colle dans les reglages du profil (desktop ou
   `<nom> setup`), puis `<nom> gateway start`. Le gateway default multiplexe deja:
   tant que le profil n'a pas son token, ses messages arrivent chez default (bien l'expliquer
   quand l'humain dit 'Bonjour <agent>').

Pieges : verrou de token (deux profils ne peuvent pas partager un bot) ; 'hermes profile
create' avertit 'no API keys' — normal, corrige par l'etape 2 ; ls profiles/ renvoie
'aucun' au tout debut (le dossier profiles/ n'existe qu'apres le premier create).
