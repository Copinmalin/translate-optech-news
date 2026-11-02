---
title: 'Bulletin Hebdomadaire Bitcoin Optech #47'
permalink: /fr/newsletters/2019/05/21/
name: 2019-05-21-newsletter-fr
slug: 2019-05-21-newsletter-fr
type: newsletter
layout: newsletter
lang: fr
---
Cette semaine, le bulletin décrit la proposition de soft fork bip-anyprevout, résume quelques présentations techniques de la conférence
Magical Crypto Friends, et inclut nos rubriques régulières sur la prise en charge de l'envoi vers bech32 et les changements notables dans
les projets populaires d'infrastructure Bitcoin.

{% include references.md %}

## Mesures à prendre

*Aucune cette semaine.*

## Nouvelles

- **Modes de sighash anyprevout proposés :** il y a deux semaines, Anthony Towns a [publié][email bip-anyprevout] un BIP proposé sur les
  listes de diffusion Bitcoin-Dev et Lightning-Dev pour examen. L'idée, [bip-anyprevout][], fournit deux nouveaux modes de hachage de
  signature (sighash) qui permettent à une signature de s'engager sur moins de détails concernant les fonds dépensés que le mode sighash par
  défaut de [bip-taproot][] et [bip-tapscript][]. Cela permet la fonctionnalité précédemment décrite par [BIP118][] avec une modification
  afin qu'elle fonctionne avec Taproot et réduise le risque de mauvaise utilisation accidentelle. L'un des nouveaux modes de sighash est
  directement compatible avec la couche [Eltoo][] proposée pour LN, ne nécessitant que des modifications pour Taproot et l'ajout d'une
  *signature chaperon* (décrite plus loin). Un second mode de sighash s'engage sur davantage de données que nécessaire pour Eltoo d'une
  manière qui peut le rendre utile pour des engagements atypiques dans Eltoo ou pour une utilisation dans d'autres protocoles.

  Un avantage significatif de cette proposition par rapport à BIP118 noinput est qu'elle peut tirer parti des dépenses coopératives Taproot,
  permettant aux deux parties ou plus d'un canal LN ou d'un autre protocole de contrat de dépenser leurs fonds de manière optionnelle sans
  révéler aucun des termes du contrat (y compris le fait qu'anyprevout était utilisé).

  Pour un aperçu rapide d'anyprevout, nous l'examinons dans le contexte d'un canal LN à deux parties basé sur Eltoo. Pour rappel, la
  caractéristique clé d'Eltoo est que chaque changement de solde dans un canal (mise à jour d'état) peut être dépensé par *n'importe quelle*
  mise à jour d'état ultérieure, il n'y a donc aucun risque de publier un ancien état dans la chaîne de blocs comme c'est le cas avec les
  canaux LN actuels basés sur des pénalités. Eltoo appelle cette capacité le *rebinding* et BIP118 proposait de rendre le rebinding possible
  en permettant aux signatures de ne pas s'engager sur la partie entrée de la transaction de dépense---permettant à quiconque de modifier
  cette partie de la transaction pour lier n'importe quel état ultérieur dont il avait connaissance.

  Le mode `SIGHASH_ANYPREVOUTANYSCRIPT` (toute sortie précédente, tout script) défini par bip-anyprevout fonctionne de manière similaire à
  BIP118 noinput, avec les changements suivants. Pour utiliser anyprevoutanyscript, la clé publique à laquelle une signature est comparée
  devra utiliser un préfixe spécial (0x00 ou 0x01 ; à ne pas confondre avec les clés publiques utilisées pour la clé de sortie de
  [bip-taproot][bip-taproot], qui utilise le même préfixe dans un contexte différent). De plus, le script en cours d'évaluation devra
  contenir au moins une signature qui n'utilise pas anyprevoutanyscript ni l'autre nouveau mode de sighash décrit plus loin. Cette signature
  non-anyprevout est appelée la *signature chaperon* parce que, sous des hypothèses raisonnables, elle empêche qu'une signature anyprevout
  soit utilisée à mauvais escient. (Voir le [Bulletin #34][] pour les détails concernant le problème de rejeu.) Avec le préfixe correct et
  une signature chaperon, anyprevoutanyscript permet à la signature de ne pas s'engager sur l'identifiant de la sortie dépensée
  (l'outpoint), le scriptPubKey de cette sortie précédente, et le hachage de la feuille taproot exécutée (tapleaf). Le condensé de
  transaction sur lequel la signature s'engage inclut toujours certains détails sur le prevout, tels que sa valeur en bitcoins.

  De plus, bip-anyprevout définit aussi un autre mode de sighash : `SIGHASH_ANYPREVOUT` qui requiert également le même préfixe spécial de
  clé publique et une signature chaperon, mais inclut le scriptPubKey du prevout et le hachage du tapleaf dans la signature. Alors que
  anyprevoutanyscript peut permettre un rebinding de type Eltoo où tout état ultérieur peut se lier à tout état antérieur (mais les états
  antérieurs ne peuvent pas se lier aux états ultérieurs), il peut exister des protocoles alternatifs (et des moments au sein du protocole
  Eltoo) où les participants veulent s'assurer que l'état *n* ne puisse se lier qu'à l'état *n-1* et à aucun autre état.

  La proposition a commencé à recevoir des [retours][anyprevout list] sur les listes de diffusion, donc nous fournirons des mises à jour
  dans les bulletins suivants résumant toute discussion significative.

- **Présentations d'intérêt technique à la conférence Magical Crypto Friends :** Bryan Bishop a fourni des [transcriptions][mcf transcripts]
  d'environ une douzaine de présentations et panels de la conférence MCF il y a deux week-ends, et les organisateurs de la conférence ont
  mis en ligne la plupart des [vidéos][mcf vids]. Bien que seule l'une des présentations ait décrit des développements spécifiquement
  nouveaux, plusieurs d'entre elles ont discuté des détails et implications de technologies telles que les transactions confidentielles,
  taproot, schnorr, et d'autres idées liées à Bitcoin. Nous avons trouvé les présentations suivantes particulièrement intéressantes :

  - Une [présentation][mcf andytoshi] d'Andrew Poelstra sur la cryptographie utilisée dans les cryptomonnaies. En particulier, il se
    concentre sur la difficulté de construire des systèmes où *tout* doit être fait correctement afin de résister aux attaques.

  - Un [panel][mcf nonet] de Rodolfo Novak, Elaine Ou, Adam Back, et Richard Myers sur l'utilisation de Bitcoin sans accès direct à
    Internet. Les sujets abordés comprenaient la propagation des blocs par satellite, les réseaux maillés, la radio amateur, et le transport
    physique de données (sneakernets), ainsi que la manière dont ils peuvent rendre Bitcoin plus robuste pour les utilisateurs actuels et
    plus accessible pour les utilisateurs dans des zones avec un accès réseau limité. Nous avons trouvé particulièrement intéressante une
    discussion annexe sur la sécurité du relais des données Bitcoin---en bref, le protocole Bitcoin est déjà conçu pour accepter sans
    confiance des données de pairs aléatoires, donc le relais hors réseau ne modifie pas nécessairement le modèle de confiance.

  - Une [conversation][mcf future ln] entre Will O'Beirne, Lisa Neigut, Alex Bosworth avec la modération de Leigh Cuen discutant de l'avenir
    de LN, principalement de la conclusion à court et moyen terme des efforts de développement actuels autour de la spécification LN 1.1. Il
    n'y a pas d'affirmations exagérées dans cette discussion, mais une simple description de la manière dont on peut s'attendre à ce que LN
    s'améliore d'une façon qui facilite son adoption par les utilisateurs et les entreprises.

## Prise en charge de l'envoi Bech32

*Semaine 10 sur 24 d'une [série][bech32 series] sur la manière de permettre aux personnes que vous payez d'accéder à tous les avantages de
segwit.*

{% comment %}<!-- weekly reminder for harding: check Bech32 Adoption
wiki page for changes -->{% endcomment %}

{% include specials/bech32/10-snooze-lose.md %}

## Changements notables dans le code et la documentation

*Changements notables cette semaine dans [Bitcoin Core][bitcoin core repo], [LND][lnd repo], [C-Lightning][c-lightning repo],
[Eclair][eclair repo], [libsecp256k1][libsecp256k1 repo], et [Bitcoin Improvement Proposals (BIPs)][bips repo].*

- [Bitcoin Core #15006][] étend la RPC `createwallet` avec un nouveau paramètre `passphrase` qui permet de créer un nouveau portefeuille
  chiffré par défaut. Les portefeuilles existants peuvent toujours être convertis en portefeuilles chiffrés avec la RPC `encryptwallet`.

- [Bitcoin Core #15870][] modifie la façon dont les RPC `importwallet`, `importpubkey`, `importaddress`, et `importprivkey` interagissent
  avec l'élagage. Auparavant, elles échouaient si l'élagage était activé. Cependant, l'élagage peut être configuré pour une opération
  manuelle (`prune=1`) ou réglé sur une valeur supérieure à la taille actuelle de la chaîne de blocs (par ex. `prune=450000`), fournissant
  des cas où l'élagage est activé mais où tous les blocs peuvent toujours être présents. Avec cette fusion, les appels n'échouent que si des
  blocs manquent réellement à cause de l'élagage. Alternativement, les utilisateurs peuvent appeler la RPC `importmulti` qui permettra
  d'importer n'importe quelles clés ou autres données même si des blocs ont été élagués tant que l'heure de création des données
  (horodatage) se situe dans la plage des blocs qui n'ont pas encore été élagués.

- [Bitcoin Core #14802][] accélère la RPC `getblockstats` de plus de 100x (tel que mesuré par Optech) en utilisant les données d'annulation
  du chainstate---les données utilisées pour ramener le registre à un état antérieur lors d'une réorganisation de la chaîne de blocs. Cela
  supprime également la dépendance de cette RPC à l'index des transactions (txindex).

- [Bitcoin Core #14047][] et [Bitcoin Core #15512][] ajoutent les fonctions requises pour le [protocole de transport v2 chiffré][] décrit
  dans le [Bulletin #39][]. Ce n'est qu'un petit sous-ensemble de l'ensemble des modifications requises ; voir la [PR #14032][Bitcoin Core
  #14032] principale pour plus de détails.

- [C-Lightning #2631][] étend l'utilitaire pylightning avec trois nouvelles méthodes : `autoclean` configure la suppression automatique des
  factures expirées (par défaut un jour après leur expiration). `check` détermine si une commande est valide sans l'exécuter.
  `setchannelfee` permet de définir les frais pour les paiements relayés, soit des frais de base ajoutés à tout paiement relayé, soit des
  frais en pourcentage appliqués proportionnellement au montant du paiement.

- [C-Lightning #2627][] étend pylightning avec une méthode `deleteinvoice` qui supprime toutes les factures ayant expiré avant l'heure
  spécifiée.

{% include linkers/issues.md issues="15006,15870,14802,14047,2631,2627,15512,14032" %}
[mcf transcripts]: https://diyhpl.us/wiki/transcripts/magicalcryptoconference/2019/
[v2 transport protocol]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-March/016806.html
[anyprevout list]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/lightning-dev/2019-May/001992.html
[mcf vids]: https://www.youtube.com/playlist?list=PLWqtMh0tDnEGBHDS8CalOpkVZhlIgRlAC
[mcf andytoshi]: https://diyhpl.us/wiki/transcripts/magicalcryptoconference/2019/crypto-in-cryptocurrency/
[mcf nonet]: https://diyhpl.us/wiki/transcripts/magicalcryptoconference/2019/bitcoin-without-internet/
[mcf future ln]: https://diyhpl.us/wiki/transcripts/magicalcryptoconference/2019/ln-present-and-future-panel/
[email bip-anyprevout]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-May/016929.html
[bech32 series]: /en/bech32-sending-support/
[le bulletin #34]: /fr/newsletters/2019/02/19/#discussion-sur-le-marquage-des-sorties-pour-activer-des-fonctionnalites-restreintes-lors-de-la-depense
[le bulletin #39]: /fr/newsletters/2019/03/26/#proposition-de-transport-p2p-version-2
[eltoo]: https://blockstream.com/eltoo.pdf
