# Hermes Agents — sauvegarde des profils

Trois agents spécialisés Hermes (Nous Research Hermes Agent), chacun dans son dossier de profil.
Contenu versionné : **SOUL.md** (identité), **config.yaml** (modèle/réglages), **skills/** (compétences propres),
**cron/** (tâches planifiées), **memories/** (mémoire longue), **scripts/** (outils).

| Agent | Rôle | Skills propres |
|---|---|---|
| `choral-master` | Analyse de partitions chorales SATB, voix, chœur | `music-score-analysis` |
| `gold-scalper` | Trading or XM MT5 : EAs, backtests, orchestrateur de risque | `gold-scalper-xm`, `mt5-trading-agent` |
| `video-studio` | Production vidéo pro multi-agents (scénario→packaging) | `pro-video-storyteller` + 12 `pvs-*` |

Liens externes : le trading complet (EAs + backtests) vit dans **[BEMIYERI/gold-scalper](https://github.com/BEMIYERI/gold-scalper)**.

## Restauration sur une nouvelle machine
1. Installer Hermes, créer les profils `choral-master`, `gold-scalper`, `video-studio`.
2. Copier ici → vers `%LOCALAPPDATA%\hermes\profiles\<nom>\` : `SOUL.md`, `config.yaml`, `cron/`, `memories/`, `skills/`, `scripts/`.
3. Recréer `.env` à partir de `.env.example` : coller les tokens (voir ci-dessous) — **ils ne sont pas dans ce dépôt, volontairement**.
4. Bot Telegram par profil : créer via @BotFather, mettre le token dans `.env` du profil (+ `allowed_users`), redémarrer le gateway hors session agent (`hermes gateway restart`).
5. Skills génériques (apple, creative, email, productivity…) : livrées avec l'installation Hermes, non dupliquées ici.

## Secrets — politique
`.env`, `auth.json`, `pairing/`, bases `state.db*`, sessions et caches sont **exclus par .gitignore**.
Le fichier credentials MT5 est chiffré DPAPI, lié à ce Windows : inutile et illisible ailleurs — non copié.
