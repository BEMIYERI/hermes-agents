# Multi-marché 24h/7 — rotation XM MT5 (mesures compte démo)

Objectif : continuer à trader quand le symbole principal est fermé ou sans opportunité.
Les règles restent GLOBALES : 1 position simultanée tous marchés, 1 stop journalier,
1 plancher de solde, 1 cooldown. La rotation ne doit JAMAIS devenir N moteurs parallèles.

## Pools par heure UTC (jours ouvrés ; re-mesurer si le décalage serveur change)

| Créneau UTC | Ordre de sondage | Pourquoi |
|---|---|---|
| 00–07 | USDJPY, EURUSD, GBPUSD, GOLD | Asie |
| 07–16 | EURUSD, GOLD, GBPUSD, USDJPY | Londres |
| 16–21 | GOLD, EURUSD, GBPUSD, USDJPY | New York |
| 21–24 | BTCUSD | daily break FX/GOLD = 00:00–01:00 heure SERVEUR |
| Sam–Dim | BTCUSD | seul marché 24/7 d'un serveur FX/CFD |

Faits d'horloge mesurés : serveur = UTC+3 (octobre ; suit le DST du broker, pas le tien).
BTCUSD a une MAINTENANCE quotidienne ~23:00–00:00 serveur (`order_check` retcode 10016) —
la pool FX couvre exactement cette fenêtre ; ne pas coder les créneaux depuis la mémoire,
dériver l'ouverture de la fraîcheur réelle des ticks.

## Économie mesurée par marché (lot mini)

| Symbole | Spread typique | Coût aller-retour | Marge 0.01 |
|---|---|---|---|
| USDJPY | 23 pt | $0.15 | ~$1 |
| EURUSD | 21 pt | $0.21 | ~$1.12 |
| GBPUSD | 24 pt | $0.24 | ~$1 |
| GOLD | 55 pt | $0.55 | $4.18 |
| BTCUSD | 4000 pt | $0.40 | (vérifier via order_check) |

Exclure du scalping : indices dont le `volume_min` est 1.00 (coûts RT > $5) et les symboles
affichant spread 0 (pas de liquide au moment de mesure — le zéro est un artefact de pause).
$/point au lot L : `trade_tick_value × (point/trade_tick_size) × L` — calculer PAR symbole,
jamais transposé de GOLD vers le FX.

## Sizing par marché (lot faisable)

```
risk = clamp(1% solde, 1.00, 2.50); cap = 1.6*risk; stop_jour = 1.5*risk
for L in [max_lot, 0.02, 0.01] (desc) :          # max_lot = seuil capital
    u = upp01 × L/0.01
    d = max(2×spread_pts + 15, min(int(risk/u), 4×ATR_M1))
    # le plancher lié au spread PRIME sur le plafond 4×ATR : refuser quand
    # 2×spread+15 > 4×ATR rend le FX calme jamais tradable (taux de rejet 100%)
    if d×u <= cap : choisir (L, d) ; break
else : refuser ce marché
TP = 2×d ; spread ≤ 50% de d (35% bloque GOLD/BTC entièrement)
```

Plafonds de spread par marché (pts) : GOLD 65, EURUSD 30, GBPUSD 35, USDJPY 35, BTCUSD 6000.
Effet attendu : les jambes FX tournent à 0.02, GOLD/BTC restent à 0.01 — même risque $, lots différents.

## Boucle de rotation (1×/minute, cron no_agent)

1. Pool de l'heure UTC courante ; scanner dans l'ordre de priorité.
2. Par symbole : fraîcheur (`tick.time − ouverture dernière bougie < 180 s`, même horloge),
   EMA9/21 M1 alignés sur EMA9/21 M15, bande RSI, whipsaw `rng(10) ≤ 4×ATR`, plafond de spread,
   lot/SL faisables, puis pré-vol `order_check` (retcode 0 ou 10009 = OK ;
   `chk.margin < margin_free×0.9`).
3. Un symbole refusé à la pré-vol est SKIPPÉ et le scan CONTINUE — l'inverse fige la rotation
   sur un marché mort au lieu de basculer.
4. Premier passage complet = une position (magic fixe). Journaliser chaque refus avec son motif : ce sont les données d'apprentissage.
5. Gardes inchangés et globaux : 1 position tous marchés, cooldown par ticket d'entrée, max trades/jour,
   stop journée sur ledger LOCAL, plancher de solde, time-exit + trailing.

## Tableau de bord multi-symboles (un seul indicateur MQL sur un chart)

- Calculs EMA/RSI/ATR par symbole via `CopyClose/CopyHigh/CopyLow` (M1 et M15) — pas de handles, pas d'abonnement au Market Watch.
- Freshness : `refT = max(tick.time sur les marchés)` ; ligne vivante si `refT − tick.time < 240`.
  `TimeCurrent()` SE FIGE quand le symbole du chart est en daily break → tout marquer FERME à tort.
- Une ligne = un label (`\n` ne rend pas), `»` sur le marché de la pool courante, `PlaySound` +
  `SendNotification` à la transition PAR symbole (tableaux d'état par marché), jamais `Alert()`.
- Un indicateur à 0 buffer n'apparaît PAS dans le Navigateur : déclarer 1 buffer factice `DRAW_NONE`.
- Le panneau affiche le signal BRUT ; l'exécuteur est plus strict (ATR, whipsaw, marge, pools).
  Un « BUY ✓ » au panneau n'est pas un ordre — ne jamais laisser l'utilisateur confondre les deux.

## Attacher / recharger l'indicateur multi-symboles (recette vérifiée)

- Un `.mq5` fraîchement compilé est INVISIBLE dans le Navigateur tant que le terminal ne redémarre
  pas : F5, Actualiser et les expansions d'arbre ne rescannent pas le disque. Ne pas chercher la
  ligne manquante — redémarrer.
- Recharger un binaire compilé : le bouton OK de la boite Propriétés NE recharge PAS l'ex5 quand
  aucun input n'a changé. Supprimer (dialogue Ctrl+I — boutons Propriétés/Supprimer/Fermer, il n'y
  a PAS d'Ajouter ici) puis double-clic sur la ligne du Navigateur ; activer d'abord le chart
  cible, le double-clic attache au chart ACTIF.
- L'arbre du Navigateur est virtualisé : après un redémarrage les lignes changent de position —
  cliquer « Indicateurs » puis flèche Droite pour déplier ; les indicateurs customs apparaissent
  APRÈS le dossier « Free Indicators » ; re-énumérer les rectangles avant le double-clic.
- Ctrl+S peut ouvrir une boîte « Enregistrer sous » qui vole le focus et bloque toute automation
  ensuite : la fermer (Entrée ou WM_CLOSE) avant de reprendre.

## Cohabitation avec les trades manuels (magic = 0)

- Une position magic=0 sans SL/TP, ouverte juste après une alerte du panneau, SANS aucune ligne
  d'EA dans `MQL5\Logs` à cette seconde = trade manuel de l'utilisateur. Ne jamais la fermer
  d'office : attacher SL/TP (`TRADE_ACTION_SLTP`, sizing de l'exécuteur, retcode 10009), journaliser
  la sécurisation, et informer.
- L'exécuteur peut continuer à trader sa position unique tant que : total ≤ 2 positions ET chaque
  étrangère a un SL (> 0). Au-delà : gel des entrées + carte d'alerte. Un gel déclenché puis levé
  ne doit pas laisser de cooldown artificiel : remettre `last_entry_ts` à 0 quand le gel n'a jamais
  abouti à un trade.
- Séquence d'entrée sûre : order_send → state/watches/journal → carte. Jamais la carte avant
  l'état, et le formatage de carte testé en exécution réelle (les accidents d'arguments de
  formatage sont arrivés APRÈS un ordre rempli).
- Les positions d'exécuteurs FRÈRES (autres magics du même agent — ex. swing 777201 vs data
  777301) sont bloquantes dans les DEUX sens : chaque module vérifie le magic de l'autre avant
  son entrée. « 1 position globale » = exclusion mutuelle, pas une règle par module ; deux
  executeurs qui ne se connaissent pas empilent légalement 2 positions sur un compte à 1 position.

## Activation mécanique des marchés (validateur → markets.json)

Répondre à « trade sur tous les marchés » n'est jamais oui/non : valider chaque marché, activer
ce qui passe, et re-juger le verdict périodiquement sans intervention.

- L'exécuteur ne codera PAS la liste de marchés dans son code : il lit à chaque tick un
  `markets.json` et ne trade que `auto=true`. L'ordre du fichier = l'ordre de priorité de scan
  (marché validé en tête).
- Un validateur (cron hebdo `no_agent`, script déterministe — pas de LLM) rejoue le backtest
  2 ans et réécrit le fichier. Critère binaire : `n ≥ 20 ET IS > 0 ET OOS > 0 ET risque médian
  ≤ cap`. Un marché actif qui échoue est désactivé automatiquement ; l'humain n'est plus requis
  pour chaque bascule.
- **Pitfall critique : le validateur doit reproduire la logique de SKIP du moteur live** (skip
  des entrées risque > cap notamment). Un backtest sans le cap compte des trades que le moteur
  ne prendra jamais : le même marché passait « REJETE (risque max 181$) » sans le cap et
  « ACTIF (IS/OOS positifs) » avec — seul le second décrit le comportement réel.
- Force humain : `force: true` + motif dans le JSON. Le validateur PRÉSERVE le flag et l'état
  auto du marché forcé — sinon la révision hebdo écrase la décision humaine silencieusement.
  Déforcer = retirer le flag, la validation reprend la main.
- Tout marché forcé contre le verdict porte un **ledger PnL par marché** (cumul mensuel, visible
  sur chaque carte de sortie) : quand l'utilisateur force contre les chiffres, ce sont ses
  résultats réels qui arbitrent plus tard — pas l'ancien backtest, pas une opinion.

## Module de collecte sans SL (refus du SL comme consigne persistante)

Un utilisateur qui refuse le SL de façon répétée : livrer `SL_MODE = NONE | PROTECT (1.2×ATR) |
WIDE (3×ATR)` — commutable en une ligne, les trois livrés, et chaque carte d'entrée affiche
« SANS SL » en face. Ne jamais retirer silencieusement la protection, ne jamais bloquer le
système sur ce désaccord.

- Le time-exit DURA remplace le SL : durée max dure imposée par le module ; le superviseur
  avertit et ferme manuellement si une position dépasse durée+10 min (time-exit raté = fermeture
  immédiate + pause). C'est le substitut que l'humain accepte.
- Sorties = TP ou time-exit UNIQUEMENT. Pas de soft stop ni trailing dans un module de mesure :
  des sorties bidouillées contaminent la distribution mesurée (le soft stop à 0.8R a été prouvé
  AGGRAVANT en scalp M1 — il se déclenche sur le bruit).
- Les filtres qui biaisent l'échantillon (whipsaw, planchers ATR) sont ENREGISTRÉS mais non
  bloquants : un collecteur mesure, il ne trie pas. Champs par entrée : px, spread, RSI, ATR,
  distances EMA9/21, régime HTF, ratio rng(10)/ATR, tp_pts, lot, solde, rang du jour.
- À la clôture, enrichir de MFE/MAE via `copy_rates_range` sur les barres entrée→sortie : c'est
  ce qui répond « où aurait dû être le SL » sans l'avoir risqué. Convertir les temps barres
  serveur→UTC avec `off = tick.time − int(time.time())` mesuré à l'appel — jamais deux horloges
  différentes dans la même requête.
- Survivre même pour de la data : 1 position globale (exclusion mutuelle des modules frères,
  cf. above), stop journalier PROPRE au module, plancher de solde, max trades/jour, fichier de
  pause partagé.
- **Un mode DRY (env var de test) doit aussi supprimer les EFFETS DE BORD** — pas seulement
  l'ordre : écritures dataset/journal, dedup de barre (sigbar), cooldown. Sinon les passes de
  test injectent des phantom-entrées dans le dataset et consomment le signal de la barre en
  cours ; le dataset analysable est vicié dès la naissance. Filets de sécurité : filtrer les
  lignes fantômes (clé inconnue côté close) et purger les sigbars de test avant la live.

## Weltrade SyntX specifics (mesures 2026-10-02)

- **filling_mode=1 (IOC)**, pas FOK. FOK refuse (retcode 10030), IOC passe (10009).
- **tick_value=$0.01** au lot 0.01 — 1 point = $0.0100, pas $1.00 comme XM GOLD.
- **Spreads** : FX Vol 60 = 407 pts, FX Vol 20 = 428 pts, SFX Vol 20 = 398 pts, SFX Vol 60 = 407 pts.
- **SFX Vol 20/60** : bid=ask=0 via API — non tradeables, à exclure du scan.
- **Scalping M1 impossible** : 0/10080 bougies M1 > spread sur FX Vol. Seul SWING H1 viable (~30% bougies H1 > spread).
- **TP_min** : FX Vol 60 = 2713 pts, FX Vol 20 = 2853 pts (15% du spread).
- **EA attachment** : pywinauto UIA Navigateur tree vide sur Weltrade. Déployer .ex5 dans le bon dossier Experts de l'instance, redémarrer le terminal, puis attacher manuellement via Navigator. Ne pas compter sur l'auto-attach UIA.
- **2 positions = couloirs par catégorie** (1 GOLD + 1 AUTRES), lock cross-engine gsa_slot_lock.json (150s). Les positions manuelles (magic=0) comptent dans les couloirs.
