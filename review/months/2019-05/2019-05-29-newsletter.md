---
title: 'Bulletin Hebdomadaire Bitcoin Optech #48'
permalink: /fr/newsletters/2019/05/29/
name: 2019-05-29-newsletter-fr
slug: 2019-05-29-newsletter-fr
type: newsletter
layout: newsletter
lang: fr
---
Le bulletin de cette semaine décrit la nouvelle proposition d’opcode `OP_CHECKOUTPUTSHASHVERIFY`, couvre la discussion continue sur Taproot,
et fournit un lien vers une présentation vidéo sur la gestion de l’augmentation des frais de transaction Bitcoin. Sont également incluses
nos rubriques habituelles sur la prise en charge de l’envoi vers bech32, les questions et réponses les plus votées de Bitcoin Stack
Exchange, et les changements notables dans les projets populaires d’infrastructure Bitcoin.

{% comment %}<!-- include references.md below the fold but above any Jekyll/Liquid variables-->{% endcomment %}
{% include references.md %}
{% include specials/2019-exec-briefing/fees.md %}

## Mesures à prendre

*Aucune cette semaine.*

## Nouvelles

- **Proposition d’un nouvel opcode pour les engagements de sorties de transaction :** Jeremy Rubin a publié sur la liste de diffusion
  Bitcoin-Dev une proposition de soft fork pour ajouter un opcode `OP_CHECKOUTPUTSHASHVERIFY` qui permet à une adresse Bitcoin d’exiger que
  la transaction qui la dépense inclue un certain ensemble de sorties. Cela permet une forme restreinte de covenants Bitcoin qui peut être
  utilisée pour réduire la quantité de données qui doivent être placées onchain dans certaines situations, réduisant potentiellement les
  coûts ou améliorant la confidentialité dans ces cas. Pour plus de détails, veuillez consulter la [section spéciale de ce bulletin à propos
  de la proposition][].

- **Poursuite de la discussion à propos de bip-taproot et bip-tapscript :** deux commentaires cette semaine issus de la discussion sur la
  liste de diffusion Bitcoin-Dev ont semblé particulièrement dignes d’intérêt :

  - *Pile finale vide :* dans les scripts legacy, segwit, et proposés [bip-tapscript][], un script est évalué avec succès s’il contient
    exactement[^legacy-cleanstack] un élément qui est *vrai*. Russell O'Connor a [soulevé][emptystack1] un point qu’il a [déjà soulevé
    auparavant][emptystack0] et a demandé que cette opportunité soit saisie pour exiger que tapscript ne soit évalué avec succès que s’il se
    termine avec une pile vide. Pieter Wuille a [répondu][emptystack reply] que son travail sur [miniscript][] (voir le [Bulletin #32][]) a
    montré que, pour le sous-ensemble de scripts que miniscript créera, ce changement de sémantique n’économiserait au plus que 0,25 vbytes
    par tapscript. De plus, bien que ce changement puisse simplifier le développement pour quiconque écrit des scripts à la main, il est un
    peu risqué car tous les guides de développement sur Script écrits à ce jour enseignent que les scripts doivent se terminer avec une
    valeur *vraie* sur la pile. Wuille a résumé : « globalement, cela semble donc être quelque chose avec des coûts marginaux, mais aussi
    tout au plus des bénéfices marginaux. »

  - *Déplacer l’octet de parité :* les clés publiques Bitcoin sont le plus naturellement spécifiées à l’aide d’une paire de coordonnées X,Y,
    comme cela se faisait aux premiers temps de Bitcoin avec les [clés publiques non compressées][]. Cependant, comme une clé publique
    valide doit se trouver sur la courbe elliptique, il est possible de trouver les deux coordonnées Y valides (l’une impaire, l’autre
    paire) pour toute coordonnée X donnée à partir de la formule de la courbe. Dans le format de clé compressée, le premier octet contient
    un seul bit pour indiquer si la coordonnée Y est impaire ou paire, suivi de 32 octets pour encoder la coordonnée X. Le bip-taproot
    proposé suivait cette convention et utilisait 33 octets pour encoder la clé de sortie taproot.

    Cette semaine, John Newbery a [suggéré][smaller v1 spk] que nous utilisions une méthode pour éviter de placer cet octet dans le
    scriptPubKey. Wuille a convenu que cela pourrait être utile et tentera de mettre en œuvre une variante où le bit sera inclus dans les
    données witness taproot. Cela réduira le coût de création d’une sortie taproot d’un vbyte (la rendant identique à P2WSH actuellement).
    {% comment %}<!-- with either zero or 0.25 vbytes additional cost to spend a taproot output. (harding note: I'm confused by where the
    bit is being placed, so moving this clause into a comment) -->{% endcomment %}

- **Présentation : un retour aux frais :** pendant la Blockchain Week NYC plus tôt ce mois-ci, le contributeur de Bitcoin Optech Mike
  Schmidt a donné une présentation sur les frais de transaction Bitcoin lors du premier briefing d’Optech axé sur les dirigeants. La [vidéo
  de sa présentation][vid return to fees] est désormais disponible. {{return-to-fees}}

## Engagements proposés de sorties de transaction

L’opcode [proposé][bip-coshv] `OP_CHECKOUTPUTSHASHVERIFY` permet à une adresse Taproot de s’engager envers un ou plusieurs tapscripts qui
exigent que la transaction qui les dépense inclue un certain ensemble de sorties, une technique que les chercheurs en protocoles
contractuels appellent un *covenant*. Le principal avantage décrit pour cet opcode proposé est de permettre à une petite transaction d’être
confirmée maintenant (lorsque les frais peuvent être élevés) et que cette transaction garantisse sans confiance qu’un groupe de personnes
recevra ses paiements réels plus tard, lorsque les frais pourraient être plus bas. Cela peut être bien plus économique pour les
organisations qui mettent déjà en œuvre des techniques telles que le [batching de paiements][topic payment batching] pour gérer des hausses
soudaines de frais.

Avant d’examiner le nouvel opcode lui-même, prenons un moment pour voir comment vous pourriez accomplir quelque chose de similaire à l’aide
des fonctionnalités actuelles des transactions Bitcoin.

Alice veut payer un ensemble de dix personnes mais les frais de transaction sont actuellement élevés, de sorte qu’elle ne veut pas envoyer
dix transactions séparées ni même utiliser le batching de paiements pour envoyer une transaction qui inclut une sortie pour chacun des
destinataires. À la place, elle veut s’engager sans confiance à les payer dans le futur sans avoir à payer maintenant des frais onchain pour
dix sorties. Alice demande donc à chacun des destinataires une de ses clés publiques et crée une transaction *d’installation* non signée et
non diffusée qui paie ces clés à l’aide d’un script multisig 10-sur-10. Puis elle crée une transaction enfant qui dépense depuis la sortie
multisig vers les 10 sorties qu’elle voulait initialement créer. Nous appellerons cette transaction enfant la transaction de *distribution*.
Elle demande à tous les destinataires de signer cette transaction de distribution et s’assure que chaque personne reçoive les signatures de
tous les autres, puis elle signe et diffuse la transaction d’installation.

![Une transaction d’installation finançant une transaction de distribution présignée](/img/posts/2019-05-tx-tree-1.png)

Lorsque la transaction d’installation reçoit un nombre raisonnable de confirmations, il n’existe aucun moyen pour Alice de reprendre son
paiement aux 10 destinataires. Tant que chacun des destinataires possède une copie de la transaction de distribution et toutes les
signatures des autres, il n’existe pas non plus de moyen pour un destinataire de priver un autre destinataire d’un paiement. Donc, même si
la transaction de distribution qui paie effectivement les destinataires n’a pas été diffusée ni confirmée, les paiements sont sécurisés par
la transaction d’installation confirmée. À tout moment, n’importe lequel des destinataires qui veut dépenser son argent peut diffuser la
transaction de distribution et attendre sa confirmation.

Cette technique permet aux payeurs et aux destinataires de verrouiller un ensemble de paiements pendant des frais élevés, puis de ne
distribuer les paiements effectifs que lorsque les frais sont plus faibles. D’après les estimations de frais de Bitcoin Core au moment de la
rédaction, toute personne assez patiente pour attendre une semaine qu’une transaction soit confirmée (comme la transaction de distribution
ci-dessus) peut économiser significativement sur les frais. Examinons l’exemple ci-dessus dans ce contexte. Pour rendre les comparaisons
ultérieures avec Taproot plus équitables, nous supposerons qu’une certaine forme d’agrégation de clés et de signatures est utilisée, telle
que [MuSig][] ou (en théorie) l’ECDSA multipartite (voir le [Bulletin #18][]).

{% assign p2wpkh = "Une transaction dépensant une entrée P2WPKH vers deux sorties P2WPKH" %}
{% assign batched11 = "Une transaction dépensant une entrée P2WPKH vers onze sorties P2WPKH, soit 9*(8+1+22) octets de plus que la transaction P2WPKH à deux sorties" %}
{% assign batched10 = "Une transaction dépensant une entrée P2WPKH vers dix sorties P2WPKH, soit 8*(8+1+22) octets de plus que la transaction P2WPKH à deux sorties" %}

| | Paiements individuels | Paiement groupé | S’engager maintenant, distribuer plus tard | |-|-|-|-| | Transactions immédiates (frais
élevés) | 10x<abbr title="{{p2wpkh}}">141 vbytes</abbr> | 1x<abbr title="{{batched11}}">420 vbytes</abbr> | 1x<abbr title="{{p2wpkh}}">141
vbytes</abbr> | | Coût à 0.00142112 BTC/KvB | 0.00204641 | 0.00059687 | 0.00020037 | | Transactions différées (frais faibles) | --- | --- |
1x<abbr title="{{batched10}}">389 vbytes</abbr> | | Coût à 0.00001014 BTC/KvB | --- | --- | 0.00000394 | | Total vbytes | 1,410 | 420 | 530
| | Coût total | 0.00204641 | 0.00059687 | 0.00020431 | | **Économies par rapport à la colonne précédente** | --- | **71%** | **66%** |

Nous voyons que ce type de paiement différé sans confiance peut permettre une économie de 66% par rapport au batching de paiements et de 90%
par rapport à l’envoi de paiements séparés. Notez que les économies pourraient être encore plus importantes pendant des périodes de plus
grande stratification des frais ou avec plus de dix destinataires.

### CheckOutputsHashVerify

Le soft fork proposé ajouterait un nouvel opcode, `OP_CHECKOUTPUTSHASHVERIFY` (abrégé par son auteur en `OP_COSHV` avec un *S*
supplémentaire). Cet opcode et un condensat de hachage pourraient être inclus dans des scripts tapleaf, lui permettant d’être l’une des
conditions d’une adresse Taproot. Lorsque cette adresse serait dépensée, si COSHV était exécuté, la transaction de dépense ne serait valide
que si le condensat de hachage de ses sorties correspondait au condensat de hachage lu depuis le script par COSHV.

En comparant cela à notre exemple ci-dessus, Alice demanderait à nouveau à chacun des participants une clé publique (comme une adresse
Taproot[^taproot-pubkeys]). Comme précédemment, elle créerait 10 sorties qui paieraient chacune l’un des destinataires --- mais elle
n’aurait pas besoin d’en faire une transaction de distribution spécifique. À la place, elle ferait simplement le hachage des dix sorties
ensemble et utiliserait le condensat résultant pour créer un script tapleaf contenant COSHV. Ce serait le seul tapleaf dans cet engagement
Taproot. Alice pourrait également utiliser les clés publiques des participants pour former la clé interne taproot afin de leur permettre de
dépenser coopérativement l’argent sans révéler le chemin de script Taproot.

![Une transaction d’installation payant une sortie COSHV qui se déploie en transaction de distribution](/img/posts/2019-05-tx-tree-2.png)

Alice donnerait alors à chacun des destinataires une copie des dix sorties pour leur permettre de vérifier que la transaction d’installation
d’Alice, une fois suffisamment confirmée, leur garantissait le paiement. Lorsqu’ils voudraient plus tard dépenser ce paiement, n’importe
lequel d’entre eux pourrait alors créer une transaction de distribution contenant les sorties engagées. Contrairement à l’exemple de la
sous-section précédente, ils n’ont rien à présigner, ils n’auraient donc jamais besoin d’interagir les uns avec les autres. Encore mieux,
les informations qu’Alice doit leur envoyer afin de leur permettre de vérifier la transaction d’installation et finalement de dépenser leur
argent pourraient être envoyées par des méthodes de communication asynchrones existantes telles que l’email ou un disque cloud. Cela
signifie que les destinataires n’auraient pas besoin d’être en ligne au moment où Alice a créé et envoyé sa transaction d’installation.

Cette élimination du besoin d’interaction est un point particulièrement marquant de la proposition. Si nous imaginons l’exemple ci-dessus
avec Alice étant une plateforme d’échange, la forme interactive du protocole exigerait qu’elle garde les dix participants en ligne et
connectés à son service à partir du moment où chacun d’eux soumet sa demande de retrait jusqu’à ce que l’interaction soit terminée --- et
ils devraient tous utiliser des portefeuilles compatibles avec un tel protocole de signature de transaction enfant. La forme non interactive
avec COSHV n’exigerait d’eux que la soumission d’une adresse Bitcoin et d’une adresse email (ou d’une autre adresse de protocole pour la
livraison des sorties engagées).

### Retours et activation

La proposition a reçu plus de 30 réponses sur la liste de diffusion Bitcoin-Dev au moment de la rédaction. Les préoccupations soulevées
comprenaient :

- **Pas assez flexible :** Matt Corallo [dit][coshv flex], « nous devons avoir une solution flexible qui offre plus de fonctionnalités que
  seulement cela, sinon nous risquons de l’ajouter pour devoir refaire tout cet effort lorsque les gens demanderont une meilleure solution.
  »

- **Pas assez générique :** Russell O'Connor suggère que COSHV et `SIGHASH_ANYPREVOUT` (décrit dans [le bulletin de la semaine dernière][le
  bulletin
  #47]) pourraient tous deux être remplacés à l’aide d’un opcode `OP_CAT` et d’un opcode `OP_CHECKSIGFROMSTACK`.
  Les deux opcodes sont actuellement implémentés dans les sidechains [ElementsProject.org][] telles que [Liquid][blockstream liquid].
  L’opcode `OP_CAT` [concatène][catenates] deux chaînes en une seule chaîne et l’opcode `OP_CHECKSIGFROMSTACK` compare une signature sur la
  pile à d’autres données sur la pile plutôt qu’à la transaction qui contient la signature. La concaténation permet à un script d’inclure
  diverses parties d’un message qui sont combinées avec des éléments witness au moment de la dépense afin de former un message complet qui
  peut être vérifié à l’aide de `OP_CHECKSIGFROMSTACK`.

  Parce que le message qui est vérifié peut être une transaction Bitcoin --- y compris une copie partielle de la transaction que le
  dépensier tente d’envoyer --- ces opérations permettent à un script d’évaluer des données de transaction sans avoir à lire directement la
  transaction en cours d’évaluation. Comparez cela à COSHV qui examine le hachage des sorties et à anyprevout qui examine toutes les autres
  signatures de la transaction.

  Un inconvénient potentiellement majeur de l’approche cat/checksigfromstack est qu’elle exige des witnesses plus volumineux pour contenir
  le script plus grand et tous ses éléments witness. O'Connor a noté qu’il ne verrait pas d’inconvénient à passer à des implémentations plus
  concises (comme COSHV et anyprevout) une fois qu’il sera clair qu’un nombre significatif d’utilisateurs utilisent effectivement ces
  fonctions via des modèles génériques.

- **Pas assez sûr :** Johnson Lau a souligné que COSHV permet la réutilisation de signature de manière similaire à [BIP118][] noinput, un
  risque perçu que [bip-anyprevout][] s’efforce d’éliminer.

Rubin et d’autres ont fourni au moins des réponses préliminaires à chacune de ces préoccupations. Nous nous attendons à ce que la discussion
se poursuive, nous rendrons donc compte des développements significatifs lors des prochaines semaines.

Le [BIP proposé pour COSHV][bip-coshv] suggère qu’il pourrait être activé en même temps que bip-taproot (si les utilisateurs le souhaitent).
Comme bip-taproot lui-même est encore en discussion, nous ne recommandons pas que quiconque en vienne à attendre une activation conjointe.
Les discussions futures et les tests d’implémentation révéleront si chaque proposition est suffisamment mûre, suffisamment souhaitable, et
suffisamment soutenue par les utilisateurs pour justifier son ajout à Bitcoin.

Globalement, COSHV semble fournir une méthode simple (mais ingénieuse) pour permettre aux sorties de s’engager sur l’endroit où leurs fonds
peuvent finalement être envoyés. Dans le bulletin de la semaine prochaine, nous examinerons d’autres façons dont COSHV pourrait être utilisé
pour améliorer l’efficacité, la confidentialité, ou les deux.

## Prise en charge de l’envoi vers Bech32

*Semaine 11 sur 24 dans une [série][bech32 series] sur la manière de permettre aux personnes que vous payez d’accéder à tous les avantages
de segwit.*

{% comment %}<!-- weekly reminder for harding: check Bech32 Adoption
wiki page for changes -->{% endcomment %}

{% include specials/bech32/11-only-bech32.md %}

**Correction du Bulletin #46 :** notre section à propos des codes QR bech32 affirmait incorrectement que les adresses bech32 utilisées dans
des URI BIP21 avec des paramètres supplémentaires ne pouvaient pas utiliser le mode alphanumérique majuscule des QR. Nadav Ivgi nous a
aimablement [informés][ivgi tweet] que les codes QR pouvaient mélanger les modes. Nous avons mis à jour [ce paragraphe][updated qr
paragraph] avec les informations correctes, quelques détails supplémentaires, et un ensemble additionnel d’exemples de codes QR.

*Si vous remarquez des erreurs dans un bulletin Optech ou dans toute autre documentation que nous publions, veuillez nous envoyer un
[email][optech email], un [tweet][optech twitter], ou contacter autrement l’un de nos [contributeurs][optech contributors].*

## Questions et réponses sélectionnées de Bitcoin Stack Exchange

*[Bitcoin Stack Exchange][bitcoin.se] est l’un des premiers endroits où les contributeurs d’Optech cherchent des réponses à leurs questions
--- ou lorsque nous avons quelques moments libres pour aider des utilisateurs curieux ou confus. Dans cette rubrique mensuelle, nous mettons
en lumière certaines des questions et réponses les mieux votées publiées depuis notre dernière mise à jour.*

{% comment %}<!-- https://bitcoin.stackexchange.com/search?tab=votes&q=created%3a1m..%20is%3aanswer -->{%
endcomment %}
{% assign bse = "https://bitcoin.stackexchange.com/a/" %}

- [Quelles sont les limitations pour amortir la configuration de session interactive de MuSig ?]({{bse}}87605) Richard Myers tente
  d’optimiser la configuration interactive pour un système à faible bande passante, mais l’utilisateur nickler souligne que les nonces ne
  doivent pas être réutilisés sous peine de voir des clés privées divulguées. Nickler poursuit en fournissant des suggestions pour atteindre
  l’objectif de Myers.

- [Coût onchain de Segwit version 1 par rapport à version 0 ?]({{bse}}87697) L’utilisateur Wapac demande une comparaison du poids de
  transaction entre segwit v0 et v1, en particulier pour des transactions simples à clé unique. Andrew Chow fournit des détails au niveau de
  l’octet et conclut que v1 est toujours moins cher à dépenser, tandis que v0 peut être moins cher pour créer une sortie. Cependant, Andrew
  souligne que l’expéditeur n’a généralement pas beaucoup de choix quant au type de sortie vers lequel il envoie, donc les utilisateurs
  préféreront probablement v1 même pour les transactions à clé unique. Wapac fournit aussi une réponse présentant un tableau récapitulatif.

- [Segwit v1 inclut-il v0 ?]({{bse}}87612) Pieter Wuille déclare que non, vous ne pouvez pas utiliser des [scripts v0][BIP141] à l’intérieur
  d’une [dépense v1][bip-tapscript]. Il précise que la raison en est que, pour atteindre certains des objectifs derrière v1, il faut une
  incompatibilité avec certains aspects du script v0.

- [Négociations de frais dans Lightning.]({{bse}}87586) Mark H décrit comment, dans un exemple de paiement LN à quatre sauts, les frais sont
  négociés.

## Changements notables dans le code et la documentation

*Changements notables cette semaine dans [Bitcoin Core][bitcoin core repo], [LND][lnd repo], [C-Lightning][c-lightning repo],
[Eclair][eclair repo], [libsecp256k1][libsecp256k1 repo], et [Bitcoin Improvement Proposals (BIPs)][bips repo].*

- [LND #3098][] augmente le nombre maximal de blocs pendant lesquels le démon attendra la confirmation d’une transaction de financement de
  canal initiée par un pair distant, le faisant passer de 288 blocs (deux jours) à 2 016 (deux semaines). Cela permet aux utilisateurs
  patients de payer des frais de transaction plus faibles.

- [C-Lightning #2647][] spécifie un répertoire de plugins par défaut à partir duquel les plugins seront automatiquement chargés même si les
  paramètres de configuration `--plugin` ou `--plugin-dir` ne sont pas spécifiés. Actuellement, il s’agit du répertoire `plugins` dans le
  répertoire de configuration du démon lightning.

- [C-Lightning #2650][] ajoute un nouveau hook de plugin lorsqu’un pair distant tente d’ouvrir un canal avec le nœud local. Cela permet au
  plugin de rejeter l’ouverture du canal ou d’effectuer d’autres actions avant que le canal ne soit ouvert.

- [Eclair #952][] ajoute une méthode `sendtoroute` qui permet aux utilisateurs de sélectionner manuellement le canal par lequel un paiement
  est initialement routé. Cela peut leur permettre de choisir quels canaux se retrouvent vidés de leurs fonds.

- [Eclair #965][] permet à l’utilisateur de spécifier la préimage lors de la création d’une facture. Cela peut être utilisé pour des
  systèmes qui génèrent de manière sécurisée des identifiants de facture impossibles à deviner, tels qu’un [atomic swap][] ou un ensemble de
  termes contractuels combinés avec un nonce au [format pay-to-contract][p2c].

## Nouveau calendrier de publication

À partir de cette semaine, le bulletin Optech sera publié chaque mercredi au lieu de chaque mardi. Cela nous donnera un jour ouvrable
supplémentaire pour relire et éditer les brouillons du bulletin avant publication.

## Remerciements particuliers

Nous remercions Jeremy Rubin et Anthony Towns pour leurs relectures d’un brouillon de ce bulletin, notamment pour nous avoir décrit l’idée
de l’arbre de sorties. Nous remercions également Pieter Wuille de nous avoir aidés à mieux comprendre où l’interaction est nécessaire dans
l’agrégation des clés et des signatures avec MuSig. Toute erreur dans la version publiée de ce bulletin est de la responsabilité de
l’auteur.

## Notes de bas de page

[^legacy-cleanstack]: Segwit v0 (P2WSH) et la proposition Tapscript exigent que la pile finale ne contienne qu’un seul élément *vrai* pour
réussir. Cela s’appelle la règle *cleanstack*. Le script legacy pour les sorties nues et les sorties P2SH permet à la pile de contenir
plusieurs éléments et de réussir tant que l’élément au sommet de la pile à sa terminaison est *vrai*. Cependant, les transactions legacy qui
n’ont pas une pile propre ne seront ni relayées ni minées par la politique par défaut du mempool de Bitcoin Core. La règle cleanstack aide à
réduire la malléabilité des transactions car tout ajout ou suppression d’éléments superflus dans un scriptSig ou un witness changera le taux
de frais d’une transaction et (pour les transactions legacy) son txid.

[^taproot-pubkeys]: Le format proposé des adresses Taproot (adresses segwit v1) inclut directement une clé publique dans l’adresse, donc
quiconque dispose d’un ensemble d’adresses Taproot peut les utiliser pour créer une clé publique agrégée. Cependant, certains utilisateurs
peuvent créer des adresses Taproot à l’aide de clés publiques pour lesquelles personne ne possède (ou ne peut plausiblement générer) la clé
privée correspondante. Pour cette raison, toute personne créant des clés publiques agrégées ne devrait probablement pas supposer que les
adresses Taproot sont elles-mêmes des clés publiques et devrait collecter des clés publiques séparées. De plus, il est probablement
préférable de ne pas réutiliser la même clé publique à plus d’un endroit dans Bitcoin. Nous omettons les étapes supplémentaires de collecte
des clés publiques dans les exemples de ce bulletin afin de simplifier les descriptions de COSHV. Veuillez envisager de consulter un expert
Bitcoin avant de mettre en œuvre les protocoles que vous lisez dans les pages de ce bulletin ou n’importe où ailleurs sur Internet.

{% include linkers/issues.md issues="3098,2647,2650,952,965" %}
[channel factories]: https://www.tik.ee.ethz.ch/file/a20a865ce40d40c8f942cf206a7cba96/Scalable_Funding_Of_Blockchain_Micropayment_Networks.pdf
[p2c]: https://arxiv.org/abs/1212.3257
[atomic swap]: https://en.bitcoin.it/wiki/Atomic_swap
[emptystack1]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-May/016935.html
[emptystack0]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2018-December/016558.html
[emptystack reply]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-May/016947.html
[elliptic curve]: https://en.wikipedia.org/wiki/Elliptic_curve
[smaller v1 spk]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-May/016943.html
[vid return to fees]: https://www.youtube.com/watch?v=ihUQ4C42KUk
[coshv flex]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-May/016936.html
[elementsproject.org]: https://elementsproject.org/
[blockstream liquid]: https://blockstream.com/liquid/
[catenates]: https://en.wiktionary.org/wiki/catenate
[uncompressed public keys]: https://btcinformation.org/en/developer-guide#public-key-formats
[ivgi tweet]: https://twitter.com/shesek/status/1131733590235131905
[updated qr paragraph]: /en/bech32-sending-support/#qrcode-edit
[optech twitter]: https://twitter.com/bitcoinoptech
[optech contributors]: /en/about/#contributors
[special section about the proposal]: #proposed-transaction-output-commitments
[bech32 series]: /en/bech32-sending-support/
[le bulletin #32]: /fr/newsletters/2019/02/05/#miniscript
[le bulletin #18]: /fr/newsletters/2018/10/23/#deux-articles-publies-sur-l-ecdsa-multipartite-rapide
[le bulletin #47]: /fr/newsletters/2019/05/21/#modes-de-sighash-anyprevout-proposes
[miniscript]: /en/topics/miniscript/
[musig]: https://eprint.iacr.org/2018/068
