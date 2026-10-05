# Apprentissage honnete : concevoir la boucle d'adaptation

Un agent qui pretend apprendre sans discipline statistique est pire
qu'un agent qui n'apprend pas : il donne une confiance fake dans des
reglages arbitraires. Cette reference definit ce que la boucle d'apprentissage
a le droit de faire.

## Le piege de l'echantillon trop petit

Avec n observations, l'ecart-type du win rate (Bernoulli) vaut :

```
sigma(wr) = sqrt( p(1-p) / n )
```

| n | sigma a p=0.5 | Ce qu'on peut conclure |
|---|---|---|
| 5 | 22.2 pts | Rien. N'importe quel hasard ressemble a une tendance. |
| 10 | 15.8 pts | Rien de defendable. |
| 20 | 11.2 pts | Marginal. |
| **30** | **9.1 pts** | Un ecart de 15 pts vaut ~1.6 sigma : seuil honnete. |
| 100 | 5.0 pts | Edge de 10 pts detectable. |
| 390 | ~2.6 pts (par bras) | Edge reel de 10 pts, powee 80%. |

**Minimum 30 observations resolues** avant toute adaptation, ET
`sigma(wr) <= 0.15`. Une regle qui s'arrete a 5 echantillons reglera un
parametre sur du bruit — c'est exactement le defaut le plus courant dans les
EA « auto-learning ».

## Separation in-sample / out-of-sample

Chronologique, 70% / 30% des observations resolues.

- Un setup n'est promeu que si **l'OOS confirme l'IS**.
- Si l'IS est bon et l'OOS s'effondre -> action `WARN_DEGRADED` : on signale,
  on ne desactive pas sur un OOS trop petit, mais on ne continue pas
  aveuglement non plus. Sans cette regle, un setup appris sur une bonne
  periode garde indefiniment le droit de trader alors qu'il ne fonctionne plus.
- Un OOS de moins de ~10 observations n'est pas concluant : le dire
  explicitement plutot que de trancher.

## Ce que l'apprenant a le droit de faire

- **Desactiver** un setup dont l'expectancy IS est negative ET confirmee OOS.
- **Reactiver** un setup qui recupere (IS et OOS positifs).
- **Proposer** (pas appliquer) une suggestion de seuil au superviseur.

## Ce que l'apprenant n'a JAMAIS le droit de faire

- Modifier lot, SL, TP, risque max, spread gate, kill-switch, quota journalier.
  Un systeme qui auto-adapte son propre risque sur un petit compte augmente
  son exposition precisement quand il perd.
- Inventer un nouveau setup.
- S'adapter sous le minimum d'echantillon.

Ces parametres sont **figures dans le code** et la garantie se teste :
`assert_frozen_unchanged(avant, apres)` leve si l'un d'eux bouge. C'est une
regle testee, pas une intention.

## Metriques : ne pas s'arreter au win rate

Le win rate ignore la taille des gains et des pertes. Rapporter par setup :

| Metrique | Pourquoi |
|---|---|
| n | taille d'echantillon |
| win rate + **ecart-type** | incertitude, pas juste le point |
| expectancy en R | gain moyen attendu, en multiples du risque |
| profit factor | gains bruts / pertes bruts |
| MFE / MAE | jusqu'ou le trade est alle favorable / defavorable |

Expectancy en R et profit factor sont ceux qui decident. Un setup a 70% de
win rate et expectancy negative est un setup qui perd.

## Journal : append-only, features + refus

Le journal est la source de verite. Deux regles :

1. **Append-only.** Une observation resolue est figee. C'est ce qui rend
   l'historique auditable et l'apprentissage non manipulable a posteriori.
2. **Enregistrer les refus avec leurs features**, pas seulement les executions.
   Le nombre de trades est le denominateur du win rate reel ; un journal qui
   n'enregistre que les executions l'inflime mecaniquement.

## Ce que la taille de compte rend infaisable

A 0–3 trades/jour, detecter un edge de 10 points demande ~390 trades par bras,
soit plus d'un an. Ce n'est pas un probleme de methode : c'est une limite
structurelle du capital. **Le dire** plutot que de regler contre un echantillon
qui n'atteindra jamais la significativite. Le systeme vaut alors comme banc
d'essai et producteur de donnees, pas comme machine a gagner de l'argent.

## Rollback

Chaque changement est journalise (horodatage, setup, action, raison, n IS/OOS).
Un changement qui degrade l'OOS est reverti automatiquement. Sans journal de
changements, on ne peut pas dire WHICH paramètre a produit la regression.
