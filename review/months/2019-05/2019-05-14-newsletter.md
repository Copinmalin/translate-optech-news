---
title: 'Bulletin Hebdomadaire Bitcoin Optech #46'
permalink: /fr/newsletters/2019/05/14/
name: 2019-05-14-newsletter-fr
slug: 2019-05-14-newsletter-fr
type: newsletter
layout: newsletter
lang: fr
---
Le bulletin de cette semaine comprend une section spéciale sur la récente proposition Taproot, des nouvelles concernant un petit changement
potentiel du format PSBT BIP174, et nos sections habituelles sur la prise en charge de l'envoi vers des adresses bech32 et les changements
notables dans les projets d'infrastructure populaires.

{% include references.md %}

## Mesures à prendre

*Aucune cette semaine.*

## Dashboard items

- **Frais plus élevés :** au moment de la rédaction, les estimations de frais pour une confirmation dans les 2 prochains blocs sont dix fois
  plus élevées que les estimations pour une confirmation dans les 30 blocs (six heures) et cent fois plus élevées que les estimations pour
  attendre 144 blocs (1 jour) ou plus. Cela peut signifier qu'il existe encore une opportunité de consolider à faible coût un nombre modeste
  d'entrées au cas où les frais augmenteraient encore davantage, mais seulement si vous pouvez tolérer une attente potentiellement longue
  pour que la transaction de consolidation soit confirmée.

## Nouvelles

- **Discussion sur le soft fork :** plusieurs réponses ont été publiées sur la liste de diffusion Bitcoin-Dev en réponse à [bip-taproot][]
  et [bip-tapscript][]. De plus, Anthony Towns a [publié][anyprevout post] une proposition pour une modification supplémentaire par soft
  fork qui utilise des fonctionnalités de bip-taproot pour activer une fonctionnalité similaire dans son objectif à [BIP118][]
  SIGHASH_NOINPUT. Comme le bulletin de cette semaine comprend déjà une section spéciale sur Taproot, nous reportons les résumés des retours
  et de cette extension au bulletin de la semaine prochaine afin que les lecteurs puissent d'abord prendre le temps d'assimiler l'essentiel
  de Taproot.

- **Ajout des chemins de dérivation aux PSBT BIP174 :** Stepan Snigirev a [publié][psbt path] une suggestion sur la liste de diffusion
  Bitcoin-Dev pour permettre aux PSBT d'inclure la clé publique étendue BIP32 (xpub) et le chemin de dérivation des clés publiques utilisées
  pour générer l'adresse de la sortie de monnaie. Cela peut aider les portefeuilles multisig à déterminer si la sortie de monnaie de la
  transaction retourne ou non au bon ensemble de signataires. L'auteur de [BIP174][], Andrew Chow, était réceptif à l'idée, tout comme le
  développeur d'un portefeuille matériel.

## Vue d'ensemble des BIP proposées Taproot et Tapscript

La semaine dernière, Pieter Wuille a [envoyé][taproot post] à la liste de diffusion Bitcoin-Dev des liens vers deux BIP proposées. La
première, [bip-taproot][], permet de dépenser en utilisant soit une signature de type Schnorr, soit un script merklisé. La seconde,
[bip-tapscript][], définit une légère variation du langage Script existant de Bitcoin à utiliser dans les dépenses merkle bip-taproot.

Pour les lecteurs déjà familiers avec le scripting Bitcoin et des idées comme [MAST][], il devrait être possible de comprendre directement
les BIP. Pour les lecteurs ayant moins de contexte, nous avons préparé le résumé suivant de certaines fonctionnalités clés des propositions
en les examinant du point de vue d'un portefeuille existant qui souhaite être mis à niveau pour utiliser Taproot et Tapscript. Cela
n'effleure que la surface de ce que ces propositions rendent possible, car l'une des raisons pour lesquelles les développeurs attendent les
signatures Schnorr et les contraintes basées sur MAST est qu'elles fournissent les briques de base pour de nouvelles fonctionnalités qui
étaient auparavant difficiles ou impossibles à construire sur Bitcoin. Nous laisserons la description de ces avancées pour une autre fois et
nous concentrerons ici sur la manière dont les deux BIP proposées peuvent faire fonctionner des usages existants de Bitcoin encore mieux
qu'aujourd'hui.

Veuillez noter que toutes les fonctionnalités de Taproot seront sur adhésion volontaire pour les portefeuilles, donc aucun portefeuille
existant n'aura besoin de changer son fonctionnement. Seuls les portefeuilles qui veulent tirer parti des avantages de Taproot et Tapscript
devront être mis à niveau.

### Ce qui n'est pas dans les propositions

Avant d'examiner quelles fonctionnalités les propositions peuvent ajouter à Bitcoin, prenons un moment pour examiner certaines choses qui ne
font pas partie des propositions :

- **Pas d'agrégation de signatures inter-entrées :** tout comme les transactions Bitcoin actuelles, chaque entrée devra contenir toutes les
  signatures requises. Cela signifie que les transactions telles que les consolidations et les coinjoins ne recevront aucune réduction
  particulière. Si les propositions Taproot et Tapscript deviennent partie intégrante de Bitcoin, nous pensons que les développeurs
  continueront à chercher des moyens d'apporter l'agrégation de signatures inter-entrées à Bitcoin dans de futurs soft forks, mais ils
  devront trouver des moyens de résoudre les [complications][sigagg complications] découvertes au cours de leurs recherches sur les
  techniques avancées décrites par bip-taproot. (Voir le [Bulletin #3][] pour une discussion connexe dans le contexte de [bip-schnorr][].)

- **Pas de nouveaux types de sighash :** bien que certains types de sighash existants soient légèrement ajustés, les propositions n'offrent
  rien de similaire à [BIP118][] SIGHASH_NOINPUT. Cependant, bip-tapscript fournit un mécanisme de compatibilité ascendante (clés publiques
  étiquetées) qui facilitera l'extension des opcodes de vérification de signature par de futurs soft forks avec de nouveaux types de sighash
  ou d'autres modifications.

- **Aucun mécanisme d'activation spécifié :** si les utilisateurs décident qu'ils veulent commencer à appliquer les nouvelles règles du soft
  fork, la sécurité exige qu'un nombre suffisant d'entre eux commence à appliquer les nouvelles règles au même bloc afin que les mineurs
  soient dissuadés de créer des blocs qui violent ces nouvelles règles. Divers mécanismes ont été utilisés pour accomplir cela dans le passé
  et d'autres options ont été décrites pour un usage potentiel futur. Cependant, bip-taproot ne mentionne aucune de ces techniques. Optech
  est d'accord avec l'auteur principal de la BIP sur le fait que [la discussion sur l'activation est prématurée][discuss activation]. Nous
  devons d'abord nous assurer qu'il existe un large consensus sur le fait que les propositions sont sûres et souhaitables avant de commencer
  un débat sur la meilleure façon de les activer.

### Dépense single-sig à l'aide de Taproot

Pour examiner ce qui se trouve dans les propositions, nous étudierons principalement comment des cas d'utilisation existants pourraient être
transférés vers Taproot. Le meilleur point de départ consiste à examiner la manière dont la plupart des fonds sont transférés via le
protocole Bitcoin en ce moment : les dépenses single-sig P2PKH et P2WPKH.

Les portefeuilles single-sig P2WPKH génèrent aujourd'hui une clé privée, en dérivent une clé publique (pubkey), puis hachent cette pubkey
pour créer le programme witness d'une adresse bech32. (P2PKH est fonctionnellement identique mais utilise un script différent et un encodage
d'adresse différent.)

| Object | Operation | Example result | |-|-|-| | Clé privée | lire 32 octets depuis un [CSPRNG][], ou en utilisant la dérivation HD
[BIP32][] | `0x807d[...]0101` | | Clé publique | point(0x807d[...]0101), ou en utilisant la dérivation publique HD [BIP32][] |
`0x02e5[...]3c23` | | Hachage | ripemd(sha256(0x0202e5[...]3c23)) | `0x006e[...]05d6` | | Adresse | bech32.encode('bc', 0, 0x006e[...]05d6)
| `bc1qd6[...]24zh` |

Avec Taproot, l'étape de hachage sera ignorée et l'adresse bech32 contiendra donc directement la pubkey, avec un petit changement.
Actuellement, les pubkeys de style Bitcoin de 33 octets sont encodées pour commencer soit par 0x02, soit par 0x03 afin de permettre aux
validateurs de reconstruire la coordonnée Y de la clé sur la courbe elliptique secp256k1 ; dans bip-taproot, la valeur de cet octet est
réduite de deux de sorte que 0x02 devienne 0x00 et 0x03 devienne 0x01. La signification reste la même mais l'utilisation du bit de poids
faible pour les valeurs libère les bits restants pour de futurs soft forks. De plus, la version witness passe de `0`, utilisée pour
P2WPKH/P2WSH, à `1`.

| Object | Operation | Example result | |-|-|-| | Clé privée | (Même chose que ci-dessus) | `0x807d[...]0101` | | Clé publique | (Même chose
que ci-dessus) | `0x02e5[...]3c23` | | Modifier le préfixe de clé | (key[0] - 2),key[1:33]) | `0x00e5[...]3c23` | | Adresse |
bech32.encode('bc', 1, 0x00e5[...]3c23) | `bc1pqr[...]xg73` |

Voici un exemple d'adresses existantes comparé à un exemple d'adresse taproot.

| P2PKH | `1B6FkNg199ZbPJWG5zjEiDekrCc2P7MVyC` | | P2SH | `3QsFXpFJf2ZY6GLWVoNFFd2xSDwdS713qX` | | P2WPKH |
`bc1qd6h6vp99qwstk3z668md42q0zc44vpwkk824zh` | | P2WSH | `bc1q0jnggjwnn22a4ywxc2pcw86c0d6tghqkgk3hlryrxl7nmxkylmnq6smlx3` | | Taproot |
`bc1pqrj4788jx79yn3x3wpgks3h6ex3rqgs5tk5qyjreu24vjdgu3q7zxkxxg73` |

Dépenser depuis P2PKH ou P2WPKH exige que le dépensier inclue sa clé publique dans son entrée. Pour Taproot, la clé publique a été fournie
dans l'UTXO dépensé, donc plusieurs vbytes sont économisés en ne l'incluant pas à nouveau. La dépense doit également inclure une signature ;
il s'agit d'une signature de type Schnorr telle que définie par [bip-schnorr][] avec un octet sighash facultatif ajouté. Si le sighash par
défaut est utilisé, la signature fait 64 octets (16 vbytes) ; si un sighash non par défaut est utilisé, elle fait 65 octets (16,25
vbytes[^vbytes-decimal]). Globalement, cela rend le coût de création et de dépense d'une sortie Taproot single-sig environ 5 % plus élevé
que P2WPKH. Cela n'est probablement pas significatif : le coût de création d'une sortie Taproot est presque le même que celui de création
d'une sortie P2WSH---que les gens paient tout le temps sans problème---et le coût de dépense d'une Taproot à clé unique est 40 % moins élevé
que P2WPKH.

<table style="text-align: center;"> <tr> <th style="border-bottom-style: none;"></th> <th colspan="3">Vbytes</th> </tr> <tr> <th
style="border-top-style: none;"></th> <th>P2PKH</th> <th>P2WPKH</th> <th>Taproot</th> </tr> <tr> <th>scriptPubKey</th> <td>25</td>
<td>22</td> <td>35</td> </tr> <tr> <th>scriptSig</th> <td>107</td> <td>0</td> <td>0</td> </tr> <tr> <th>witness</th> <td>0</td>
<td>26.75</td> <td>16.25</td> </tr> <tr> <th>Total</th> <td>132</td> <td>48.75</td> <td>51.25</td> </tr> </table>

Outre le passage d'ECDSA à Schnorr pour l'algorithme de signature, il existe quelques changements importants (mais faciles à mettre en
œuvre) dans le condensat de transaction---le hachage auquel une signature s'engage afin de prouver que la transaction constitue une dépense
autorisée d'un UTXO.

{:#tagged-hashes} Le plus notable est que le hachage utilisé passe du double-SHA256 (SHA256d) du protocole historique à une unique opération
SHA256. Le hachage supplémentaire précédemment utilisé n'est pas censé avoir fourni une sécurité significative. De plus, les données hachées
sont préfixées par une valeur spécifique à cet usage de la fonction de hachage ; cela aide à prévenir des problèmes comme [CVE-2012-2459][]
où un hachage d'un contexte peut être utilisé dans un autre contexte. L'étiquette de préfixe est `SHA256(tag) || SHA256(tag)` où le tag est,
dans ce cas, la chaîne UTF-8 "TapSighash" et `||` représente la concaténation. Les logiciels qui ont besoin de créer ou vérifier un grand
nombre de signatures (comme les nœuds LN actifs ou les nœuds complets Bitcoin) peuvent utiliser une version de leur fonction SHA256
pré-initialisée avec l'étiquette de préfixe afin de ne pas avoir à répéter ces opérations pour chaque vérification de signature. Les
implémentations qui ne requièrent pas des performances maximales (comme les portefeuilles ordinaires) peuvent simplement implémenter
l'algorithme tel que décrit en utilisant leur fonction SHA256 par défaut.

{:#digest-changes} Il existe également quelques changements concernant les données incluses dans le hachage et leur sérialisation. Cela
comprend des améliorations qui peuvent aider les portefeuilles sans accès à des entrées UTXO vérifiées (par ex. les portefeuilles matériels
et les [HSMs][]) à être plus efficaces, car ils n'ont pas besoin de récupérer autant de données afin de s'assurer qu'ils signent pour les
bons UTXO et les bons montants.

Bien que cela puisse sembler représenter un nombre significatif de changements, nous soupçonnons qu'il ne s'agit que d'un après-midi de
travail pour effectuer des changements mineurs de sérialisation dans n'importe quel portefeuille déjà compatible segwit et pouvant accéder à
une bibliothèque telle que [libsecp256k1][] pour générer des signatures compatibles bip-schnorr.

## Dépense multisig simple à l'aide de Taproot

Après les UTXO single-sig, les plus courants sont les UTXO multisig simples. Ce sont des sorties qui dépendent d'un certain nombre de
signatures de pubkeys particulières mais n'ont pas d'autres conditions. Elles sont utilisées à la fois par des utilisateurs individuels (par
ex. pour exiger que plusieurs appareils fonctionnent ensemble lors d'une dépense) et par plusieurs parties à une transaction unique (par ex.
des séquestres).

Il existe deux façons d'effectuer une dépense multisig simple avec Taproot, la plus efficace étant l'agrégation de clés et de signatures
telle que décrite dans cette sous-section. Nous examinerons l'autre mécanisme dans la sous-section suivante.

Pour l'agrégation, deux clés privées ou plus sont créées et leurs pubkeys sont dérivées. Les pubkeys sont ensuite combinées en une seule
pubkey indiscernable de n'importe quelle autre pubkey Bitcoin. Celle-ci est utilisée comme programme witness segwit comme décrit dans la
sous-section précédente. Plus tard, le ou les propriétaires de certaines ou de toutes les clés privées créent des signatures qui sont
combinées en une seule signature également indiscernable de n'importe quelle autre signature bip-schnorr. Celle-ci doit s'engager sur le
même condensat de transaction que décrit dans la sous-section précédente, mais le résultat est une dépense multisig complètement
indiscernable d'une dépense single-sig.

Vous avez peut-être remarqué que le paragraphe précédent reste vague sur le mécanisme exact utilisé pour agréger les clés et les signatures.
La raison en est qu'il existe plusieurs méthodes connues et que n'importe laquelle d'entre elles peut être utilisée par les participants. Il
est même possible que des chercheurs trouvent de nouvelles méthodes et les implémentent dans des portefeuilles Bitcoin sans aucun changement
du consensus. Cela est possible parce que l'algorithme de signature ne recherche qu'une seule pubkey et une seule signature valides selon
les règles décrites dans la sous-section single-sig ci-dessus. Cela dit, parmi les méthodes connues, le [protocole MuSig][musig] est
probablement le protocole d'agrégation le mieux étudié dans le contexte de Bitcoin.

Le nombre d'octets utilisés pour les clés et signatures agrégées est exactement le même quel que soit le nombre de signataires impliqués.
Cela peut être comparé au multisig P2WSH où chaque pubkey supplémentaire ajoute 8,50 vbytes et chaque signature supplémentaire ajoute
environ 18,25 vbytes.

![Taille du multisig taproot comparée au P2WSH](/img/posts/2019-05-taproot-multisig-size.png)

## Dépense complexe avec Taproot

Le langage Script de Bitcoin permet aux utilisateurs de spécifier quelles conditions doivent être remplies pour que leurs bitcoins puissent
être dépensés, des conditions qui nécessitent parfois plus que de simples signatures. Taproot non seulement prend en charge cette
fonctionnalité mais l'améliore également de plusieurs façons.

Nous pouvons l'examiner en prenant un contrat de verrouillage par hachage et temps (HTLC) basique similaire à ceux utilisés dans LN et les
swaps atomiques inter-chaînes. Ce contrat peut se terminer de trois façons :

1. Alice reçoit l'argent prévu par le contrat (un paiement) en publiant une préimage qui libère le verrouillage par hachage du contrat.
2. Bob reçoit l'argent prévu par le contrat (un remboursement) après qu'un verrou temporel a expiré.
3. Alice et Bob se mettent mutuellement d'accord sur la façon de répartir l'argent, généralement parce que l'un d'eux pourrait utiliser
   l'une des conditions précédentes pour forcer un paiement ou un remboursement.

En prenant l'exemple des HTLC dans LN, nous pouvons produire deux scripts indépendants, chacun gérant l'un des deux premiers éléments
ci-dessus :

```
(1) OP_HASH256 <hash> OP_EQUALVERIFY <Alice pubkey> OP_CHECKSIG
(2) <time> OP_CHECKLOCKTIMEVERIFY OP_DROP <Bob pubkey> OP_CHECKSIG
```

Ces scripts séparés sont ensuite hachés afin de pouvoir être utilisés comme feuilles d'un arbre de merkle. Comme décrit plus tôt, les
données à hacher sont préfixées par un tag (lui-même haché) indiquant leur objectif. "TapLeaf" est le tag dans ce cas. Les feuilles doivent
également inclure la taille du script et une version (seule la version 0xc0 est définie dans cette proposition ; d'autres versions sont
disponibles pour de futures mises à niveau par soft fork).

Après le hachage des deux scripts, leurs condensats sont placés dans un ordre lexicographique. Cet ordre permettra plus tard la vérification
d'une preuve d'inclusion merkle sans savoir si chaque feuille ou branche apparaissait dans l'arbre à gauche ou à droite de son frère pair,
réduisant ainsi la quantité de données qui doit être communiquée tout en améliorant potentiellement la confidentialité. Après
ordonnancement, les deux hachages seront hachés ensemble avec le tag de préfixe "TapBranch". Comme cet arbre de merkle n'a que deux
feuilles, le hachage résultant est la racine merkle.

![Exemple d'arbre merkle taproot](/img/posts/2019-05-taproot-tree.png)

Cet arbre de merkle ne couvre que deux des états finaux possibles du HTLC. Pour le troisième cas où Alice et Bob s'accordent mutuellement
sur une dépense, ils peuvent utiliser l'agrégation de signature au moyen de quelque chose comme MuSig. Comme dans la section multisig
ci-dessus, ils travaillent ensemble pour créer une seule pubkey, appelée la *clé interne Taproot.*

La racine merkle et la clé interne sont ensuite hachées ensemble (tag de préfixe, "TapTweak") et le condensat résultant est utilisé comme
clé privée à partir de laquelle une pubkey est dérivée, cette valeur étant connue sous le nom de *tweak.* La pubkey de tweak est ajoutée à
la clé interne afin de dériver la *clé de sortie taproot---*la clé qui est utilisée dans toutes les adresses bech32 et les scriptPubKeys qui
paient ces trois conditions.

![Construction du tweak taproot et de la clé de sortie](/img/posts/2019-05-taproot-tweak.png) {:.center}

Quand vient le moment de dépenser cet argent, soit Alice soit Bob peut fournir le script qu'il souhaite utiliser, les données nécessaires à
celui-ci (une signature et, dans le cas d'Alice, une préimage de hachage), la clé interne Taproot, et le hachage du script qu'il n'a pas
utilisé. Alternativement, Alice et Bob peuvent travailler ensemble pour utiliser l'agrégation de signatures (après prise en compte du tweak)
afin de fournir une signature en combinaison avec le même modèle de dépense à clé unique et signature unique décrit dans les sous-sections
précédentes. Tant que les données qu'ils fournissent dans l'un ou l'autre cas sont correctes, la dépense sera acceptée.

{% comment %}<!--
    P2WSH scriptPubKey: 34 witnessScript: OP_IF OP_HASH256 <hash> OP_EQUALVERIFY <A pubkey> OP_ELSE <time> OP_CLTV OP_DROP <B pubkey>
    OP_ENDIF OP_CHECKSIG 8 non-push, 4 push, 2x33 (pubkeys), 1x32 (hash), 1x4 (delta) = 114

      1. witnessScript, OP_1, preimage, Alice sig 1+114 1 1+32 1+72 = 221/4 => 55.25

      2. witnessScript, OP_0, Bob sig 1+114 1 1+72 = 189/4 => 47.25

      3. N/A (use one of the above)

    Taproot scriptPubKey: 35
      1. OP_HASH256 <hash> OP_EQUALVERIFY <Alice pubkey> OP_CHECKSIG 1 1+32 1 1+33 1 = 69

         script, preimage, A sig; internal key; leaf hash 1+69 1+32 1+64 1+33 32 = 234/4 => 58.5

      2. <time> OP_CHECKLOCKTIMEVERIFY OP_DROP <Bob pubkey> OP_CHECKSIG 1+4 1 1 1+33 1 = 41

         script, B sig; internal key; leaf hash 1+41 1+64 1+33 1+32 = 174/4 => 43.5

      3. AB sig 1+64 = 65/4 => 16.25 -->{% endcomment %}

| | scriptPubKey vbytes | witness vbytes | Total vbytes | |-|-|-|-| | P2WSH (1) Alice dépense | 34 | 55.25 | 89.25 | | P2WSH (2) Bob dépense
| 34 | 47.25 | 81.25 | | P2WSH (3) Dépense mutuelle | N/A | N/A | N/A | | Taproot (1) Alice dépense | 35 | 58.50 | 93.50 | | Taproot (2) Bob
dépense | 35 | 43.50 | 78.50 | | Taproot (3) Dépense mutuelle | 35 | 16.25 | 51.25 |

Parce que nous avons choisi d'utiliser un petit arbre et un script d'exemple simple, le coût d'utilisation de la dépense par chemin de
script Taproot est similaire au coût des données qui peuvent être omises de la branche non dépensée, conduisant à des coûts légèrement plus
élevés pour Taproot dans le cas où Alice dépense. Cependant, le cas où Bob dépense est légèrement moins cher et le cas de la dépense
mutuelle est significativement moins coûteux que n'importe laquelle des autres options (et son utilisation cacherait complètement qu'il
s'agissait d'un HTLC).

La profondeur maximale d'un arbre est de 32 niveaux, permettant à un arbre de contenir un maximum d'environ quatre milliards de scripts.
Cependant, un seul de ces scripts apparaîtrait dans n'importe quelle transaction de dépense et seuls 32 hachages directement liés à l'arbre
de merkle auraient besoin d'être générés pour prouver que le script faisait partie de l'arbre---ce qui signifie que des scripts plus
complexes que notre simple HTLC peuvent obtenir des améliorations d'efficacité bien plus importantes que celles vues ci-dessus (voir un
article axé sur [MAST][] pour plus d'informations).

### Légers changements du scripting avec Tapscript

Lors de l'utilisation de Bitcoin Script avec Taproot, certaines règles ont été modifiées, notamment :

- **Redéfinition des opcodes inutilisés et invalides :** les octets des opcodes qui n'ont jamais été attribués, ou qui ont été rendus
  invalides par Satoshi Nakamoto, ou qui ont été créés pour des mises à niveau et n'ont pas encore été utilisés, ont tous été modifiés pour
  avoir la sémantique d'un opcode `OP_SUCCESS` qui rend inconditionnellement valide tout script contenant ce code. Comme les futurs soft
  forks ne peuvent ajouter de nouvelles règles qu'en rendant invalides des choses auparavant valides, cette validité maximale aujourd'hui
  permettra une flexibilité maximale dans de futurs soft forks. Bien sûr, les receveurs choisissent les scripts qu'ils utilisent pour
  recevoir des paiements, donc personne ne devrait inclure un opcode `OP_SUCCESS` dans ses scripts jusqu'à ce qu'un soft fork lui ait donné
  une nouvelle signification appliquée par le consensus.

- **Signatures Schnorr requises :** les signatures ECDSA ne seront pas acceptées dans Tapscript.

- **Nouvelles sémantiques multisig basées sur script :** les opcodes actuels `OP_CHECKMULTISIG` et `OP_CHECKMULTISIGVERIFY` ne sont pas
  disponibles dans Tapscript. Il existe deux alternatives. Premièrement, les opcodes single-sig existants `OP_CHECKSIG` et
  `OP_CHECKSIGVERIFY` peuvent être utilisés en série. Par exemple (multisig 2 sur 2) :

  ```
  <A pubkey> OP_CHECKSIGVERIFY <B pubkey> OP_CHECKSIG
  ```

  Deuxièmement, un nouvel opcode `OP_CHECKSIGADD` (`OP_CSADD`) peut être utilisé pour incrémenter un compteur si une signature correspond à
  une clé publique spécifiée. Par exemple (2 sur 3) :

  ```
  <A pubkey> OP_CHECKSIG <B pubkey> OP_CSADD <C pubkey> OP_CSADD OP_2 OP_EQUAL
  ```

  Ce changement est effectué pour permettre la vérification par lots de plusieurs signatures, ce qui peut [accélérer significativement la
  vérification][bip-schnorr] par rapport à la vérification indépendante de chaque signature.

- **Limite sigops redéfinie :** parce que la vérification des signatures est l'opération la plus coûteuse en CPU dans Bitcoin Script, une
  première version de Bitcoin a ajouté une limite au nombre maximal d'opérations de vérification de signature (sigops) qu'un bloc pouvait
  contenir, et des versions de cette limite ont été appliquées plus tard aux scripts P2SH et segwit v0. Cependant, un problème de cette
  limite est que les mineurs doivent considérer deux facteurs lorsqu'ils tentent de sélectionner quelles transactions valides inclure dans
  un bloc : la densité de frais (frais/vbyte) et la densité de sigops (sigops/vbyte). C'est bien plus difficile que d'optimiser la
  composition d'un bloc sur la seule base de la densité de frais.

  Taproot réduit cela à un seul paramètre en exigeant que les transactions valides utilisant des dépenses Taproot incluent une certaine
  quantité de données pour chaque sigop qui réussit. La règle est une sigop gratuite, puis le witness doit contenir 50 octets de données
  pour chaque sigop supplémentaire. Comme les signatures Schnorr font au moins 64 octets, cela devrait fournir largement assez d'espace pour
  couvrir tous les usages attendus, et cela signifie que les mineurs peuvent simplement inclure les transactions Taproot valides les plus
  rentables dans leurs blocs sans se soucier des sigops.

### Résumé de Taproot et Tapscript, et prochaines étapes

Ensemble, ces propositions apportent à Bitcoin deux fonctionnalités que les développeurs souhaitent depuis des années. La première de ces
fonctionnalités, les signatures Schnorr, permettra d'accroître la confidentialité et de réduire les frais pour le nombre croissant
d'utilisateurs de Bitcoin tirant parti de la sécurité multisig (y compris les utilisateurs de LN), et la recherche sur les usages avancés de
Schnorr tels que les [scriptless scripts][] et les [discreet log contracts][] pourrait permettre de nombreuses améliorations importantes en
matière d'efficacité, de confidentialité et de contractualisation financière sans autres changements de consensus nécessaires.

La seconde fonctionnalité, MAST basé sur Taproot, permet aux développeurs d'écrire des scripts beaucoup plus complexes que ce qui est
possible aujourd'hui tout en minimisant leur impact onchain en permettant aux dépensiers de ne placer onchain que la quantité minimale de
données---réduisant les taux de frais pour les utilisateurs avancés tout en améliorant aussi leur confidentialité.

Enfin, parce qu'il y a de fortes chances que de nombreuses dépenses single-sig, multisig et basées sur MAST puissent toutes être résolues en
n'utilisant rien d'autre qu'une seule clé publique et une seule signature, il pourrait devenir beaucoup plus difficile de suivre différents
utilisateurs qui utilisent différentes fonctionnalités de Bitcoin---un avantage qui bénéficie à tous les utilisateurs de Bitcoin en rendant
la propriété des bitcoins plus difficile à suivre et donc les bitcoins plus fongibles et plus difficiles à censurer efficacement de manière
fragmentaire.

Cependant, l'avenir de ces propositions n'est pas certain. À ce stade, elles nécessitent un examen attentif par des experts en cryptographie
et du protocole Bitcoin, ainsi que par les développeurs d'applications qui prévoient d'utiliser ces fonctionnalités. Après cela, elles
devront être implémentées pour les nœuds complets, ce qui nécessitera davantage d'examen ainsi que des tests approfondis (une
[implémentation d'exemple][] est disponible, mais elle est actuellement destinée à aider les examinateurs des propositions). Enfin, il
reviendra aux personnes qui utilisent leurs propres nœuds complets pour valider leurs paiements entrants de décider si elles veulent ou non
appliquer cette proposition.

Optech ne sait pas quand---ou si---l'un de ces objectifs sera atteint, mais nous ferons de notre mieux pour vous tenir informés de toute
progression dans les futures éditions de ce bulletin.

## Bech32 sending support

*Semaine 9 sur 24. Jusqu'au deuxième anniversaire du verrouillage du soft fork segwit le 24 août 2019, le Bulletin Optech contiendra cette
section hebdomadaire qui fournit des informations pour aider les développeurs et les organisations à mettre en œuvre la prise en charge de
l'envoi bech32---la capacité de payer des adresses segwit natives. Cela [ne nécessite pas d'implémenter segwit][bech32 series] vous-même,
mais permet aux personnes que vous payez d'accéder à tous les multiples avantages de segwit.*

{% comment %}<!-- weekly reminder for harding: check Bech32 Adoption
wiki page for changes -->{% endcomment %}

{% include specials/bech32/09-qrcode.md %}

## Changements notables dans le code et la documentation

*Changements notables cette semaine dans [Bitcoin Core][bitcoin core repo], [LND][lnd repo], [C-Lightning][c-lightning repo],
[Eclair][eclair repo], [libsecp256k1][libsecp256k1 repo], et [Bitcoin Improvement Proposals (BIPs)][bips repo].*

- [Bitcoin Core #15730][] étend la RPC `getwalletinfo` avec un champ `scanning` qui indique à l'utilisateur jusqu'où le programme est arrivé
  dans le rescannage de la chaîne de blocs à la recherche de transactions affectant son portefeuille (si l'utilisateur a demandé un
  rescannage ou s'il a été déclenché automatiquement). Sinon, il renvoie simplement `false`.

- [Bitcoin Core #15930][] déprécie la RPC `getunconfirmedbalance` et les trois différents champs de *balance* dans la RPC `getwalletinfo`. À
  leur place, une RPC `getbalances` est ajoutée et fournit deux ensembles de champs. Pour les soldes que le portefeuille peut dépenser
  ("IsMine"), un champ `trusted` pour les sorties soit créées par le portefeuille lui-même, soit ayant au moins une confirmation ; un champ
  `untrusted_pending` pour les sorties dans le mempool qui paient le portefeuille ; et un champ `immature` pour les sorties issues d'une
  transaction de génération minière qui n'ont pas encore reçu 100 confirmations (le plus tôt où elles peuvent être dépensées). Pour les
  soldes que le portefeuille ne fait que surveiller ("watchonly"), les mêmes trois champs sont fournis sous un objet différent.

- [C-Lightning #2524][] enregistre les détails des tentatives échouées de relais de paiements afin de pouvoir afficher plus tard ces détails
  dans la RPC `listforwards`.

- [Bitcoin Core #15939][] supprime la cible de compilation pour Windows 32 bits, ce qui signifie qu'il n'y aura pas de binaires Win32 pour
  les futures versions de Bitcoin Core. Les éléments de preuve suggèrent que très peu (voire aucun) utilisateurs de Bitcoin Core utilisent
  Windows 32 bits.

## Remerciements

Nous remercions Anthony Towns et Pieter Wuille pour leurs relectures perspicaces d'une ébauche de la vue d'ensemble Taproot de ce bulletin.
Toute erreur restante est la faute de l'auteur du bulletin.

## Notes de bas de page

[^vbytes-decimal]: Techniquement, les vbytes sont une unité entière afin de les rendre rétrocompatibles avec l'unité des octets dans la
pondération des blocs Bitcoin historiques. Nous les utilisons dans ce document comme une unité à virgule flottante pour une précision
supplémentaire.

{% include linkers/issues.md issues="15730,15930,2524,15939" %}
[anyprevout post]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-May/016929.html
[psbt path]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-April/016894.html
[taproot post]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-May/016914.html
[mast]: https://bitcointechtalk.com/what-is-a-bitcoin-merklized-abstract-syntax-tree-mast-33fdf2da5e2f
[sigagg complications]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2018-March/015838.html
[discuss activation]: https://twitter.com/pwuille/status/1125478777084006400
[csprng]: https://en.wikipedia.org/wiki/Cryptographically_secure_pseudorandom_number_generator
[hsms]: https://en.wikipedia.org/wiki/Hardware_security_module
[musig]: https://blockstream.com/2018/01/23/en-musig-key-aggregation-schnorr-signatures/
[scriptless scripts]: http://diyhpl.us/wiki/transcripts/layer2-summit/2018/scriptless-scripts/
[discreet log contracts]: https://adiabat.github.io/dlc.pdf
[example implementation]: https://github.com/sipa/bitcoin/commits/taproot
[bech32 series]: /en/bech32-sending-support/
[le bulletin #3]: /fr/newsletters/2018/07/10/#reprise-de-la-production-de-blocs
[cve-2012-2459]: https://bitcointalk.org/?topic=102395
