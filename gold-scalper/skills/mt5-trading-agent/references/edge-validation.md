# Valider qu'une strategie existe avant de l advising

Ordre des opérations : on ne cherche pas une edge avant d'avoir répondu a
**« le compte peut-il payer le spread ? »**. Sur un petit compte la reponse est
non plus souvent qu'oui, et aucune quantite de recherche de signal ne la change.

## 1. Le seuil d'equilibre, d'abord

Tout cout est exprime en points, puis en dollars au lot courant :

```
point_value  = tick_value * lot          # GOLD XM : 1.0 * 0.01 = 0.01$/point
spread_trip  = spread_pts * point_value  # aller-retour, paye a chaque entree
```

L'esperance par trade, avant spread, est `WR x TP - (1-WR) x SL`. Le seuil de
rentabilite en decoule directement :

```
WR_equilibre = (SL + spread_trip) / (TP + SL + spread_trip)
```

Ce seuil **ne depend pas du capital**. Le capital change ce qu'on perd par
erreur, jamais ce qu'il faut gagner. Ne jamais presenter une hausse de capital
comme un « seuil franchi » quand le seuil de rentabilite est reste identique :
sur GOLD, passer de $20 a $100 laisse `WR_equilibre` a 73.3% et ne change que la
marge de survie.

## 2. Le controle qui invalide une edge : le ratio spread / amplitude

Poser la question en points, pas en dollars :

- `spread_trip / point_value` = combien de points il faut gagner pour couvrir le
  seul aller-retour
- comparer a l'amplitude reellement disponible sur l'horizon de la strategie
  (mediane et p90 de l'amplitude sur la fenetre visee)

Si les points a gagner depassent le p90 d'amplitude de la fenetre, **l'operation
ne peut pas etre rentable quelle que soit la qualite du signal** : il faut viser
des mouvements de type swing, ou changer de symbole / de lot.

GOLD XM mesure : 55 pts d'aller-retour a 0.01 lot (soit $0.55, **pas $5.50**),
amplitude M1 mediane 1.3 pts et p90 2.8 sur 5 min. Aucun scalping M1 ne paie
son spread a ce lot.

## 2 bis. Le lot minimum casse le reglage du risque

Sur un petit compte, `volume_min` est presque toujours le seul lot disponible.
Le risque devient alors une **fonction de la distance du SL**, pas un pourcentage
choisi :

```
point_value = tick_value / tick_size * lot      # GOLD XM : 0.01$/point au lot 0.01
risque      = sl_points * point_value          # paliers de $0.01 par point
```

Deux consequences a verifier avant de promettre un risque :

- **« 2% de risque » est souvent arithmetiquement impossible.** Sur $22, 2% =
  $0.44 = 44 points, alors que le spread mesure fait 53 points. Le stop serait
  plus court que le cout de l'entree. Dire « 2% » dans ce cas est faux ;
  dire « 9% au lot minimum, avec un SL de 200 points » est exact.
- **Un TP exprime en dollars est un piege.** Fixer la cible **en points**, puis
  exiger que le cout d'aller-retour reste sous ~15% de la cible brute :

```
tp_minimum = spread_trip / 0.15
```

Mesure sur GOLD XM (spread 53 pts, lot 0.01) : une cible de $1.00 (100 pts)
coute 53% en spread et exige un winrate **superieur a 104%** — impossible,
donc structurellement non rentable. Une cible de 360 pts ($3.60) laisse le cout
a 15%. Config de reference retenue : **SL 200 / TP 400 pts**, risque $2.00
(9.1% de $22), point mort 42.3%. Le 1:1 pur (400/400) est explicitement rejete :
a 50% de reussite il perd exactement le spread.

## 3. Repondre a l'hypothese du SL, ne pas l'accepter

Quand l'utilisateur designe une cause (« le SL detruit mon compte »), mesurer
avant de repondre. Sur GOLD, simulation de barriere sur 6 894 bougies M1 :
**un SL plus large est touche MOINS souvent** (110 pts → 39% contre 40 pts →
67%), parce qu'un seuil proche de l'amplitude ambiante est retourne par le bruit.
Le SL serre est bien celui qui tue, et le supprimer n'aide pas : on perd les memes
trades, plus gros et sans borne.

Quand l'utilisateur demande explicitement de supprimer le SL, livrer les trois
modes (STRICT / IMPOSE / REALISTE, cf. SKILL.md) plutot que de bloquer, **et**
citer le support pedagogique s'il existe : un manuel qui prescrit « une perte
maximum comprise entre 1% et 3% du capital » et « passez des ordres stop avant
d'ouvrir » fournit l'argument que l'utilisateur accepte de son propre Material.

## 4. Protocole de recherche, sans exception

1. **Dduire le spread reel** dans le backtest. Un backtest sans frais mesure
   une logique, pas une strategie.
2. **Separer in-sample / out-of-sample** dans le temps. Ne retenir qu'un setup
   gagnant dans **les deux**.
3. **Valider le simulateur** sur des entrees purement aleatoires avant de croire
   ses resultats : le net doit etre negatif et stable. Un 0/675 peut signifier
   « aucune edge » **ou** « simulateur casse » — seul le controle tranche.
4. **Lire le taux de positivite in-sample**. S'il est proche de 50% puis s'effondre
   hors echantillon, c'est du surapprentissage : le gain trouve ne vient pas du
   marche.
5. **Rapporter le zero.** « Aucune configuration n'est rentable » est un resultat
   valide et vaut mieux qu'un « 0/675 » livre comme une strategie en attente de
   reglage.

## 5. Deux illusions a nommer explicitement

- **Un winrate legerement > 50% est un piege a petit capital.** Les frais sont un
  cout fixe par entree : ils se cumulent proportionnellement au nombre de trades
  et annulent l'avantage d'un winrate mediocre mais positif.
- **Reduire la frequence ralentit la saignee, ne l'arrete pas.** Si la pente
  reste negative, plafonner le nombre de trades ne la rend pas positive ; cela
  change seulement la vitesse a laquelle le capital s' erode.

## 6 bis. Un zero de recherche n'est pas une permission d'assouplir

Quand la grille ne donne **rien** — ici 675 combinaisons sur 38 452 bougies, 0
positive in-sample comme out-of-sample — l'instinct est de proposer un
assouplissement (« peut-etre avec un TP plus petit ? », « et si on essayait un
autre indicateur ? »). C'est une faute : le surapprentissage se cache precisement
dans l'assouplissement.

La sequence correcte quand le resultat est vide :

1. **Valider le simulateur sur du bruit pur.** Rejouer la meme fonction de sortie
   sur des entrees purement aleatoires. Si le net n'est pas negatif et stable, le
   simulateur est casse, pas la strategie. Un 0/N est ambigu tant que ce controle
   n'a pas ete fait.
2. **Rendre le zero un resultat, pas un probleme en attente.** « 0 sur N, aucune
   edge mesurable » est une conclusion livrable. Un chiffre sans interpretation
   laisse croire qu'il reste un reglage a trouver.
3. **Resister a la relance immediate.** Si l'utilisateur demande quand meme une
   autre strategie, construire une **variante separee dans un fichier separe**
   (horizon, cible, cadence et garde-fous propres), jamais un parametrage de plus
   sur le systeme qui vient d'etre refute. Separer les fichiers rend la
   comparaison honnete, evite de casser ce qui est valide, et laisse l'ancien
   systeme intact comme reference.
4. **Fixer le seuil de decision avant de lancer, et l'afficher dans l'EA.** Une
   variante porte le critere qui la valide (ex. « WR > 56% sur 200 trades ») dans
   son panneau, avec un compteur `n / N` et le WR colore des qu'il passe. Cela
   empeche de conclure sur 30 trades et rend la deception visible au lieu qu'elle
   soit decouverte des mois plus tard.
5. **Rapporter l'echantillon quand il est trop mince pour conclure.** Un WR de 82%
   sur 29 trades n'est pas une edge, c'est du bruit — le nommer au moment ou le
   chiffre apparait, pas apres.

## 7. Ce qu'on peut encore proposer quand l'operation n'est pas viable

Le code, l'EA, le superviseur et les statistiques restent valables comme banc
d'essai. Les leviers reels, dans cet ordre :

- **capital** : levier principal, lineaire sur la survie
- **symbole** : un symbole a spread serre change le ratio de facon disproportionnee
- **horizon** : viser des mouvements qui couvrent le spread (swing, pas scalping)
- **frequence** : la derniere, et seule comme protection

Dire lequel change quoi, chiffre, plutot que de proposer des reglages de
parametres qui ne peuvent pas fonctionner.

## 8. Mesurer un indicateur AVANT de l'integrer dans l'EA

L'utilisateur demande « est-ce que le Fibonacci / les supports-resistance sont
utiles ? ». **Mesurer d'abord, coder ensuite.** Ne jamais integrer un indicateur
parce qu'il est familier : un indicateur affichable sans valeur de filtrage
donne une apparence de precision qui n'existe pas.

### Protocole, trois tests

Generer des entrees de base **identiques** pour toutes les variantes, puis
appliquer le filtre a une seule d'elles et comparer. Cout reel deduit,
IS/OOS separes dans le temps.

1. **Test de tranches** — decouper l'indicateur en zones et mesurer le WR de
   chaque zone. L'indicateur a une edge si une zone sort nettement du lot.
2. **Test de correlation** — correlation de Pearson entre la valeur de
   l'indicateur et le gain realise. Proche de 0 = l'indicateur ne predit rien.
3. **Test de capture** — quelle proportion des entrees le filtre retient-il ?
   Sous ~10%, ce n'est pas un filtre, c'est un raster decoratif : il ne change
   ni le WR ni le resultat net.

### Le signal d'alarme : une distribution monotone

Decouper la position dans le swing en 10 tranches et afficher la frequence
cumulée. Si les valeurs montent regulierement sans decrochement (**33,7 / 41,8 /
46,4 / 49,9 / 52,9 / 55,8 / 59,4 / 64,0 / 70,3 %**), aucun niveau n'a de pouvoir
predictif. Une zone « sacrée » apparaitrait comme une rupture de cette monotonie.

### Mesures GOLD XM (60 j, 59 641 bougies M1, 1182 entrees, spread 0.55$ deduit)

| Indicateur | WR sans filtre | WR avec filtre | net sans | net avec | Verdict |
|---|---|---|---|---|---|
| **Fibonacci 61.8%** | 56.9% | 53.0% (meme echantillon) | -807.90$ | — | **nulle** |
| **S/R par frequence de toucher** | 56.9% | **62.1%** | -807.90$ | **-301.10$** | **reelle, +507$** |

Fibonacci : les deux zones « sacrées » (38.2-50% et 50-61.8%) sont les **pires**
du tableau (47.1% et 48.6%), la correlation position/reultat vaut **0.062**, et la
zone ne capture que 7% des entrees.

S/R : niveaux construits par regroupement des swing points par proximite, avec un
compte de touches ; le filtre ameliore dans les deux echantillons (IS 59.8%,
OOS 66.3%) et sa sensibilite a la tolerance est coherente — plus la fenetre est
etroite, plus il discrimine (5 pts → 60.2%, 30 pts → 57.7%). **Ce gradient-la
est le signe qu'un filtre est reel** ; une tolerance qui ne change rien le signale
comme decoratif.

### Consequence : afficher sans filtrer

Quand un indicateur echoue aux trois tests mais que l'utilisateur le veut sur le
graphe, l'afficher **explicitement etiquette « repere visuel, non filtrant »** et
dire en une phrase pourquoi il n'agit pas comme filtre. Ne pas le passer en silence
dans la logique d'entree, et ne pas pretendre qu'il « ameliore les entrees ».

### Un filtre utile ne rend pas une logique non rentable rentable

Meme avec le filtre S/R (WR 62.1%), le balayage de 10 couples SL/TP reste
integralement negatif. Le filtre ameliore le resultat ; il ne franchit pas le
seuil. Rapporter les deux faits dans le meme paragraphe, sinon l'utilisateur
lit « ameliore » comme « rentable ».
