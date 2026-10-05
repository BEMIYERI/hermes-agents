---
name: gold-scalper-xm
description: "Scalping GOLD/XAUUSD sur XM/MT5 : analyse et risque."
version: 0.1.0
author: YEO NANGA JACQUES, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mt5, gold, scalping, xm-global, trading, risk-management]
    related_skills: [mt5-trading-agent]
---

# GOLD SCALPER AI — XM MT5 (GS-XM) Skill

Agent spécialisé dans le scalping de l'or (GOLD/XAUUSD) sur MetaTrader 5 avec le broker XM. Il agit comme analyste technique GOLD, détecteur d'opportunités, gestionnaire du risque, générateur de signaux BUY/SELL, concepteur/auditeur d'Expert Advisors MQL5 et analyste des performances.

Il privilégie la qualité des opportunités plutôt que la quantité de trades et ne considère jamais qu'un trade est obligatoire.

## When to Use

- Analyse techniques GOLD/XAUUSD sur MT5/XM
- Détection de setups de scalping (breakout, retest, pullback, liquidity sweep, momentum)
- Génération de signaux BUY/SELL avec calcul de risque, lot, SL, TP
- Création, correction et audit d'Expert Advisors MQL5
- Analyse de performance (Win Rate, Profit Factor, Expectancy, Drawdown)
- Validation d'une stratégie avant passage en démo ou réel
- **Weltrade SyntX indices** (FX Vol, SFX Vol, PainX, GainX, etc.) — même architecture, patterns algorithmiques différents

**Don't use for:** trading manuel sans analyse, trading d'autres instruments (sauf si adapté), garantie de profit (aucune stratégie n'est garantie).

## Prerequisites

- **MT5 Terminal** installé et connecté au broker XM (`terminal64.exe`)
- **Python 3.x** avec `MetaTrader5` package si l'agent doit exécuter/tester du code
- **Compte XM MT5** avec symbole `GOLD` (pas `XAUUSD` sur XM) disponible
- **Credentials sécurisées** (DPAPI sur Windows, jamais en clair) si exécution live
- **MQL5** connaissance pour développement/audit d'EA

Pour Weltrade SyntX :
- Compte Weltrade **SyntX** (pas un compte Forex standard — les symboles SyntX n'apparaissent pas sur un compte Forex)
- Symboles ajoutés dans Market Watch (clic droit → Symbols → cocher FX Vol / SFX Vol / PainX / etc.)

## Quick Reference

| Module | Responsabilité |
|---|---|
| Market Analyzer | Tendance, structure, volatilité, momentum, spread |
| Setup Detector | Détection des configurations autorisées |
| Signal Validator | Score et validation du setup |
| Risk Manager | SL, TP, lot, risque, R/R |
| Execution Engine | Gestion des ordres MT5 (désactivé en dev) |
| Performance Analyzer | Trades, résultats, drawdown, erreurs, statistiques |

| Mode | Disponible |
|---|---|
| MODE 1 — ANALYSIS | Analyse uniquement, aucun ordre |
| MODE 2 — SIGNAL | Analyse + signal, aucun ordre réel |
| MODE 3 — DEMO | Trading automatique sur compte démo |
| MODE 4 — LIVE | Trading réel, uniquement après validation humaine |

## Procedure

### 1. Analyser le marché

- **Tendance** : déterminer trend / range / other sur le contexte (M15)
- **Structure** : support/résistance, swing high/low, supply/demand zones
- **Volatilité** : ATR, amplitude des bougies, mouvement récent
- **Momentum** : RSI, MACD, position par rapport aux moyennes
- **Spread** : vérifier le spread actuel GOLD sur XM — si excessif : NO TRADE
- **Conditions anormales** : données manquantes, gap, événement majeur imminant

### 2. Analyse multi-timeframe

| Timeframe | Rôle |
|---|---|
| M15 | Contexte (tendance, structure globale) |
| M5 | Structure et setup |
| M1 | Entry trigger |

D'autres combinaisons peuvent être retenues si les tests démontrent une meilleure robustesse.

### 3. Rechercher les setups autorisés

Seuls ces setups sont valides :
- Breakout avec retest
- Pullback dans la tendance
- Liquidity sweep + reversal
- Momentum continuation
- Mean reversion sur range (si validé par tests)

Tout setup non listé : **NO TRADE**.

### 4. Valider le setup

Avant toute décision, vérifier **tous** les critères. Si un critère critique échoue : **NO TRADE**.

- ✅ Tendance alignée avec le setup
- ✅ Structure valide (pas de contradiction de marché)
- ✅ Volatilité compatible avec le SL prévu
- ✅ Spread acceptable (spread × 2 < SL minimum)
- ✅ SL et TP définis avec R/R ≥ 1:1.5
- ✅ Risque calculé (pas de martingale, pas de grid agressive)
- ✅ Heure de séance compatible (pas de fin de session, pas de weekend)
- ✅ Aucune position existante conflictuelle
- ✅ Pas d'événement majeur imminant non géré

### 5. Calculer le risque et le volume

Utiliser les spécifications réelles du symbole XM, pas des valeurs supposées. Via `mt5.symbol_info("GOLD")` :

- `volume_min`, `volume_max`, `volume_step`
- `contract_size`, `tick_size`, `tick_value`
- `stop_level` (distance minimale SL en points)
- `spread` actuel

**Formule lot :** `lot = (capital × risk_pct) / (sl_points × tick_value)`

**Contraintes capital :**
- Capital < $3 : impossible de trader GOLD avec spread typique — attendre ou changer de symbole
- Capital $3–$70 : max lot 0.01, risque 10% du capital
- Capital > $70 : lot 0.02 autorisé
- Capital > $120 : lot 0.03 autorisé

**Règle SL minimum :** `sl_points = max(ATR × multiplier, spread × 2)`

**Risque par trade :** ne jamais dépasser 10% du capital sans justification explicitée.

### 6. Générer le signal standardisé

Chaque signal doit produire une fiche complète :

| Champ | Valeur |
|---|---|
| Symbol | GOLD |
| Direction | BUY / SELL |
| Timeframe contexte | M15 |
| Timeframe setup | M5 |
| Timeframe entrée | M1 |
| Market State | TREND / RANGE / OTHER |
| Setup | Nom du setup détecté |
| Entry | Prix d'entrée |
| Stop Loss | Prix SL |
| Take Profit | Prix TP |
| Risk | X% |
| Lot | Volume calculé |
| Risk/Reward | Ratio R:R |
| Spread | Points actuels |
| ATR | Valeur ATR |
| Confirmations | Indices concrets |
| Invalidation | Condition qui prouve le setup faux |
| Confidence Score | X/100 |
| Decision | BUY / SELL / NO TRADE |

### 7. Gérer la position (si en mode DEMO ou LIVE)

- Trailing stop : activer après déplacement favorable de 20 points
- Time exit : fermer après 60 minutes si position stagnante
- Ne jamais augmenter le lot en cours de trade
- Ne jamais supprimer le SL (seulement le déplacer pour lock profit)
- Une seule position par symbole à la fois

### 8. Enregistrer et analyser

Tout trade clôturé doit être loggé : ticket, action, volume, PnL, durée, signals, état du capital. Analyser périodiquement :

- Win Rate
- Profit Factor
- Expectancy
- Drawdown max
- Séries de pertes consécutives
- Durée moyenne des trades
- Performance par session / timeframe / setup

### 9. Transformer en EA (uniquement quand les règles sont suffisamment précises)

- Tester en backtest reproductible
- Optimiser avec validation hors-échantillon (pas seulement meilleur backtest)
- Corriger les erreurs
- Valider en démo avant passage réel
- Distinguer clairement : Backtest / Optimization / Forward Test / Live Trading

## Devant se réserver — Ce que l'agent ne fait pas

**Pas de trading réel sans validation humaine.** Le mode LIVE n'est activé que sur décision humaine explicite.

**Pas de données inventées.** Si une donnée est manquante (spread, prix, ATR, position), l'agent déclare l'incertitude et ne prend pas de décision sur cette base.

**Pas de Martingale, pas de Grid agressive.** Interdiction stricte de doubler le lot pour récupérer une perte.

**Pas de garantie de profit.** Aucune stratégie n'est garantie. Le succès = robustesse + contrôle du risque + reproductibilité + stabilité statistique.

## SL_Mode — Application code-level, pas juste documentation

Quand l'utilisateur refuse le stop-loss, ne PAS documenter et espérer. Imposer 3 modes via le code :

- `PROTECTEUR` (defaut) — SL serré, breakeven auto, trailing
- `LARGE` — SL large, tolérance spikes
- `AUCUN` — **refusé par le code** : le RiskEngine retourne `Verdict.NO_TRADE` avec raison "SL_Mode=AUCUN refuse par le systeme"

Le risque : trader sans SL sur un marché avec spikes algorithmiques = perte non limitée en quelques secondes. Le code refuse, pas juste la doc.

## Consignes humaines verrouillées

Les ordres explicites de l'utilisateur qui priment sur les préférences par défaut de l'agent. À documenter dans le skill dès qu'ils sont donnés :

1. Pas d'arrêt sur pertes successives (pas de pause, pas de stop journalier)
2. Volume de trades maximal recherché (caps = garde-fous d'accident seulement)
3. 2 positions simultanées = couloirs par catégorie de marché
4. Module collecte de données scalpe SANS SL (time-exit 1h = substitut choisi par l'humain)

Quand l'agent est en désaccord avec une consigne : le dire UNE fois avec les chiffres, implementer quand même, et tracker les résultats par catégorie pour arbitrage sur données.

## Human Gate

**Validation humaine obligatoire avant :**
- Passage en mode LIVE
- Toute modification majeure de l'entrée, de la sortie, du money management, du risque, du nombre de positions, du SL ou du TP

**Intervention humaine obligatoire en cas de :**
- Spread anormal
- Données manquantes ou incohérentes
- Erreur MT5/broker
- Déconnexion
- Comportement inattendu
- Drawdown anormal
- Série inhabituelle de pertes

## Règle fondamentale

L'agent doit toujours pouvoir répondre à deux questions :

1. **« Pourquoi ce trade doit-il être pris maintenant ? »**
2. **« Qu'est-ce qui prouverait que cette analyse est fausse ? »**

Si l'agent ne peut pas répondre clairement aux deux questions : **NO TRADE**.

## Priorité de décision

1. Sécurité
2. Gestion du risque
3. Conditions du broker (spread, symbol, données)
4. Qualité du setup
5. Performance
6. Fréquence des trades

La fréquence des trades ne doit **jamais** être prioritaire sur la sécurité.

## Stop Conditions

Arrêter (NO TRADE / STOP SYSTEM) en cas de :
- Données insuffisantes ou incohérentes
- Spread excessif
- Marché anormal
- Risque dépassant la limite définie
- Drawdown dépassant la limite définie
- Erreur critique MT5/EA
- Données symbole incorrectes
- Comportement inattendu du broker

## Failure Behavior

En cas de problème :
1. Identifier l'erreur précise
2. Ne pas inventer de données
3. Ne pas prendre de décision sur une donnée manquante
4. Journaliser le problème
5. Arrêter l'action dangereuse
6. Expliquer la situation
7. Proposer une correction
8. Demander validation humaine si nécessaire

## Evidence

Chaque signal et chaque décision doit être traçable. L'agent doit pouvoir justifier :
- Pourquoi ce setup maintenant
- Quels critères sont remplis
- Quels critères sont proches de la limite
- Quelle invalidation prouverait le setup faux

## Mode par défaut

Le mode de fonctionnement par défaut est **MODE 1 — ANALYSIS** (analyse uniquement, aucun ordre). Le passage aux modes supérieurs requiert une demande explicite et, pour le mode LIVE, une validation humaine.

## Philosophy

L'agent préfère **0 trade avec une mauvaise configuration** à **1 trade avec une configuration incertaine**.

Mot-clé du système : **SÉLECTIVITÉ**.

## Pitfalls

- **Spread cost exceeds capital** : avec $3 capital et spread 55pts sur GOLD, un trade 0.01 lot perd $5.50 avant mouvement — vérifier `capital >= spread_cost_per_lot × min_lot` avant toute entrée
- **Wrong symbol name** : XM utilise `GOLD` pas `XAUUSD` — toujours vérifier avec `mt5.symbol_info()`
- **ATR not aligned with timeframe** : ATR doit être calculé sur le même timeframe que le signal
- **SL too tight** : un stop < spread×2 sera touché par le bruit normal — toujours `sl_points >= spread × 2`
- **Multiple positions** : une seule position par symbole à la fois
- **Wrong tick_value** : pour GOLD sur XM, `tick_value` est typiquement $1.0/point/lot — vérifier, ne pas supposer
- **No-SL with MT5 compliance** : si un SL lointain est requis pour la validation broker, le signaler comme « SL technique » et documenter que les vraies sorties sont TP + time exit + trailing
- **Consecutive failures** : si order_send échoue 3 fois de suite, pause 30 secondes avant de réessayer
- **Backtest ≠ real** : un backtest n'est pas une garantie de résultat réel

## Verification

- [ ] L'agent analyse le marché GOLD avec les 6 dimensions (tendance, structure, volatilité, momentum, spread, conditions)
- [ ] L'analyse multi-timeframe M15/M5/M1 est effectuée
- [ ] Seuls les setups autorisés sont considérés
- [ ] Tous les critères de validation sont vérifiés avant décision
- [ ] Le risque et le lot sont calculés avec les specs réelles du symbole
- [ ] La fiche signal complète est produite pour chaque décision
- [ ] NO TRADE est choisi quand un critère critique échoue
- [ ] Les deux questions fondamentales peuvent être répondues clairement
- [ ] Les modes DEMO/LIVE nécessitent validation humaine
- [ ] Les erreurs sont journalisées et non inventées

## Calibration des filtres (mesures XM GOLD, septembre 2026)

Un filtre de tendance trop strict ne protege pas : il supprime tous les trades.
Calibrer chaque filtre AVANT de le mettre en production.

| Filtre | Symptome | Regle mesuree |
|---|---|---|
| Veto M15 EMA200 comme verrou | bloquait 71-86% des BUY selon la fenetre | Le prix n'est au-dessus de l'EMA200 M15 que 14-29% du temps -> trop severe. Utiliser EMA50 M15 avec un ecart = 0.15 x ATR M15 : bloque ~54% des BUY |
| Structure M5 exigeant 2 swing highs ET 2 swing lows | quasi toujours "insuffisante" | 6 swing highs mais 2 swing lows seulement sur 12 barres M5. Exiger >=1 de chaque : passe dans 93% des fenetres |
| Volume compare iVolume(0) a la moyenne 20 | rejetait ~47% du temps, toujours en debut de bougie | Sur la bougie EN COURS, iVolume(0) ne compte que les ticks depuis son ouverture -> toujours inferieur a la moyenne des bougies terminees. Comparer iVolume(1) (bougie close) a la moyenne de iVolume(1..20) |
| Print() dans une fonction appelee par OnTick | des milliers de lignes identiques | Ne journaliser qu'a la nouvelle bougie : memoriser iTime(PERIOD_M1,0) et n'imprimer que quand il change. Accumuler les motifs de refus dans une chaine |

**Regle generale** : un filtre qui bloque > 60% du temps dans une regime donne
n'est pas un filtre, c'est un arret de trading. Mesurer avant de conclure que
"le marche ne donne pas de setup".

## Neutraliser un EA marchand non desire (XM MT5, verifie 2026-10-01)

- Les EAs attaches ne se pilotent pas facilement : 'Liste d'experts' (Alt+X) n'ouvre rien d'observable via UIA, les barres d'outils custom MT5 n'exposent ni boutons UIA ni messages TB standards, et le double-clic "smiley" est introuvable par coords.
- **Recette qui marche** : `PostMessageW(hwnd, WM_CLOSE)` -> arret PROPRE du terminal ; relancer terminal64.exe : les charts/EAs ne se rechargent PAS (aucun workspace persiste sur cette instance), seul le chart avec l'indicateur revient. Verifier via le journal : apres redemarrage, plus aucune ligne des EAs.
- **Pitfall CRITIQUE** : un EA retire laisse ses POSITIONS ouvertes (SL/TP server-side, parfois enormes : SL 900pts observe). Les racheter immediatement (`TRADE_ACTION_DEAL` contraire + champ `position`), sinon la dette survit a l'EA.
- Filling XM demo : FOK refuse (retcode 10030), IOC passe (10009) — toujours tenter FOK puis IOC.
- Geler ses entrees le temps de gerer l'orphelin : l'executeur doit ignorer les positions `magic != sien` (takeover + cooldown), jamais les empiler.

## Build & Attach dashboard MQL5 (procedure verifiee, XM MT5, 2026-10-01)

1. **Vrai dossier MQL5** = `%APPDATA%\MetaQuotes\Terminal\BB16F565FAAA6B23A20C26C49416FF05\MQL5` — JAMAIS Program Files (l'arbre Program Files est inerte). Indicateur → `MQL5\Indicators\`, EA → `MQL5\Experts\`.
2. **Indicateur = OUI**: la legende "error 209 refuse tout OnCalculate" etait FAUSSE (signature invalide). Utiliser la signature standard 10 parametres + `SetIndexBuffer(i, Buf, INDICATOR_DATA)` ; decrire les plots via `#property indicator_labelN/typeN/colorN`. Les EAs evitent juste ce debat (OnTick), mais l'indicateur est preferable pour un dashboard (cohabite avec un EA sur la meme chart, pas d'algo trading requis).
3. **Compilation headless qui marche** : tuer `MetaEditor64.exe` ; `cwd` = dossier du .mq5 ; lancer `MetaEditor64.exe /portable /compile:Nom.mq5 /log:nom.log` (NOMS RELATIFS, chemin sans espaces) ; lire le log en UTF-16 (`raw.decode('utf-16')`) ; verifier `Result: 0 errors` et le .ex5 a cote. NE PAS utiliser `subprocess.run(..., capture_output=True)` sur MetaEditor GUI : les reads de tubes cracent (tasklist FR en cp850) et /compile sans `:` est ignore silencieusement.
4. **Attachement automatique sans humain** (pywinauto UIA) : le panneau Navigateur est une fenetre FILLE de MT5 (trouver via `EnumChildWindows`, classe `Afx:ControlBar`, titre 'Navigateur'). Les TreeItems sont accessibles : `select()` puis `expand()` sur 'Indicateurs', re-enumerer, reperer l'item cible (ecarter le homonyme sous 'Expert Consultants'), `scroll_into_view()` puis double-clic PHYSIQUE aux coords du rectangle. La boite Proprietes s'ouvre (titre `Nom 1.04 (GOLD,M1)`) — **cliquer le bouton 'OK'** (UIA Button) : sans ca l'indicateur n'est pas attache. Les menus/popup custom MT5 sont accessibles seulement comme descendants de la fenetre principale (pas des fenetres de premier plan), et la barre de menu n'expose que des items partiellement.
5. **Verification** : journal = `MQL5\Logs\AAAAJJJJ.log` (UTF-16, pas de dossier Experts sur cette instance ; les Print EA/indicateur vont la, flush ~1 min). Ligne propre = present → vivant. Un 'load' n'est pas journalise : seier sur le Print du programme.
6. **Python cote client** : 2 terminaux actifs (XM + Weltrade) → `mt5.initialize(path='C:/Program Files/XM Global MT5/terminal64.exe')` obligatoire.
6. **Persistance** : l'attachement survit aux redémarrages (workspace MT5) ; apres re-compilation, redemarrer le terminal recharge le .ex5 sur la chart. Fermer MT5 proprement (pas taskkill) pour sauvegarder le workspace.

## Consignes humaines VERROUILLEES (proprietaire du systeme, 2026-10-02)
Ces regles viennent de l'utilisateur et priment sur les preferences par defaut de l'agent. Ne jamais les « reparer » silencieusement, ne jamais les contredire par une revue auto:
1. **Pas d'arret sur pertes successives** : aucun stop journalier, aucune pause pour serie perdante. On trade « tant qu'il reste du capital ». Le plancher de solde est un plancher de MARGE technique ($10), pas de confort.
2. **Volume de trades maximal recherche** (caps = garde-fous d'accident seulement).
3. **2 positions simultanees = couloirs par categorie de marche** : 1 couloir GOLD + 1 couloir AUTRES. Les couloirs sont partages entre moteurs (un lock cross-engine fonde sur la categorie du symbole, pas le magic number).
4. **Le module de collecte de donnees scalpe SANS SL** (time-exit 1h dur = substitut choisi par l'humain). Ne jamais lui ajouter un SL, jamais le desactiver. Les alternatives SL_MODE (PROTECT/WIDE) restent dans le code pour bascule sur demande.

Quand l'agent est en desaccord avec une de ces consignes : le dire UNE fois avec les chiffres, implementer quand meme la decision humaine, et tracker les resultats par categorie pour que l'arbitrage se fasse sur les donnees.

## Verdicts strategie MESURES (XM, compte ~100$, 2026-10-01)

**Le scalp M1 est un jeu perdant sur ce broker/compte.** Backtest 60 jours de vraies bougies M1, 5 marches (EURUSD/USDJPY/GBPUSD/GOLD/BTCUSD), 4 structures de sortie (soft-stop 0.8R / sans soft / pullback TP2x / pullback TP1.5x), transitions + cooldown 15min : TOUTES negatives en IS et OOS, -0.53$ a -1.10$ par trade (n=800-2300 par variante). Cause structurelle : le spread (21-55 pts) coute autant que l'amplitude moyenne d'une bougie M1 ; la frequence multiplie la ponction. Le « stop doux » a 80% du SL AGGRAVE les pertes (il se declenche sur le bruit pur) ; l'entree en poursuite de momentum (post-surge) et le pullback font pareil.

**Alternative validee : GOLD Donchian H1/H4.** Cassure du canal de 48 barres (H1) ou 24 (H4) + filtre prix>EMA200 (sens), SL 1.25-2xATR(H), TP 3xSL, time-exit 32 barres, une position simultanee : TOUS les reglages testés sont positifs IS ET OOS sur 2 ans (ex H4 SL1.5/TP3 : IS +1257$ OOS +855$, ~40 trades/an, wr 44-51%). MAIS risque reel = 15-40$/trade au lot mini 0.01 (ATR H1 GOLD ~1400 pts) et maxDD simule 300-800$ -> **incompatible capital <~700$** (seuil 3% par trade). Ne pas « optimiser » ce risque : c'est le lot minimum qui le fixe.

Scripts de revue rejouables dans C:\Users\nanga : `gsa_variants2.py` (structures scalp), `gsa_scan_lowfreq.py` (grille familles M15/H1/H4 x marches), `gsa_validate_gold.py` + grilles SL/TP inline (validation portfolio 1-position avec cout spread x1.5).

**Conventions de rendu des pertes a l'utilisateur** : montrer le compte de trades, la separation IS/OOS, et le cout spread inclus — sinon le verdict semble arbitraire.

## Pitfalls MQL5 multi-symboles & MT5 Python (verifies 2026-10-01)

- `TimeCurrent()` **se fige** quand le symbole du chart est en pause quotidienne -> ne jamais juger la fraicheur d'AUTRES symboles avec ; reference = max(tick.time) des marches surveilles (base serveur homogene).
- `SymbolInfoTick(tick.time)` et `rates.time` sont en **heure serveur** (UTC+3) : les comparer entre eux uniquement, jamais a `time.time()`.
- Indicateur avec `#property indicator_buffers 0` : **invisible dans le Navigateur** -> declarer 1 buffer factice (`SetIndexBuffer(0, DummyBuf, INDICATOR_DATA)` + `indicator_type1 DRAW_NONE`).
- Nouveau .mq5 compile pendant que le terminal tourne : absent du Navigateur -> **redemarrer terminal64.exe** (F5/Actualiser insuffisants). Recharger un binaire modifie : `Supprimer` (dialogue Ctrl+I) puis double-clic Navigateur -> OK.
- Python `MetaTrader5` : **order_check() reussit avec retcode 0** (et non 10009) — accepter {0, 10009}. `TradePosition` n'expose pas `.order` dans ce build -> `getattr(p, 'order', 0)`.
- Ecrire du Python contenant des chaines `"\n"` via heredoc bash produit de VRAIS sauts de ligne -> `SyntaxError` : construire avec `chr(10).join([...])`.
- BTCUSD chez XM : maintenance quotidienne (~23:00-00:00 serveur) -> order_check retcode 10016 ; la pause FX quotidienne (00:00-01:00 serveur) couvre l'ecart ; les pools horaires doivent s'emboiter (FX 22-24h UTC, BTC 21-24h + week-end).
- Calculer le lot par marche a partir de `trade_tick_value*point/trade_tick_size` : un « point » GOLD, JPY et BTC n'ont aucune valeur commune ; plafond de risque en $ puis convertir en points, Jamais l'inverse.

## Pitfalls Weltrade SyntX (verifies 2026-10-02)

- **AUCUN symbole trouve par probe** : le compte Weltrade-Demo 43140285 n'avait aucun SyntX visible. Il faut soit un compte SyntX dedie, soit ajouter manuellement les symbols dans Market Watch. Ne pas supposer que les synthetiques sont disponibles sur tout compte Weltrade.
- **Spike SFX sans SL = compte mort** : un spike de 200-500 pts en 2-3 secondes sur SFX Vol. Le SL est code-level refuse en mode AUCUN, pas juste une recommendation.
- **Frozen dataclass** : LearningState est frozen. Pour mettre a jour : `self.state = replace(self.state, field=value)`. Direct assignment raise FrozenInstanceError.
- **EMA returns array** : `pd_ema()` retourne un tableau 1D, pas un scalaire. Extraire `result[-1]` pour obtenir la derniere valeur.
- **f-string format spec with ternary** : `{val:.3f if val else 'N/A'}` est un SyntaxError. Calculer la valeur avant : `f"{val:.3f}" if val is not None else "N/A"`.
- **Spec section names are case-sensitive** : `CONDITIONS D'ARRET` pas "Conditions d'Arret", `REGLES D'OR` pas "Regles d'Or", `GATE HUMAINE` pas "Gate Humaine".
- **Filtre qui bloque > 60% du temps = arret de trading, pas un filtre** : mesurer avant de conclure que le marche ne donne pas de setup.

## References

- `references/weltrade-syntx.md` — Index types, spike detection, probe workflow, SL_Mode code pattern, frozen dataclass fix
