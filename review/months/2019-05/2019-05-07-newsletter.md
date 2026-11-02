---
title: 'Bulletin Hebdomadaire Bitcoin Optech #45'
permalink: /fr/newsletters/2019/05/07/
name: 2019-05-07-newsletter-fr
slug: 2019-05-07-newsletter-fr
type: newsletter
layout: newsletter
lang: fr
---
Le bulletin de cette semaine met en lumière certains des changements de Bitcoin Core 0.18.0 récemment publié, mentionne brièvement deux BIP
proposés, décrit comment les adresses bech32 sont compatibles vers l'avant avec les améliorations attendues du protocole, et résume les
changements notables dans les projets d'infrastructure Bitcoin populaires.

{% include references.md %}

## Mesures à prendre

- **Envisagez de passer à Bitcoin Core 0.18.0 :** publiée la semaine dernière, la dernière version de Bitcoin Core apporte de nouvelles
  fonctionnalités, des améliorations de performances et des corrections de bogues. Voir la section *nouvelles* ci-dessous pour plus de
  détails.

## Nouvelles

- **Bitcoin Core 0.18.0 publié :** cette nouvelle version majeure contient plusieurs nouvelles fonctionnalités importantes ainsi que de
  nombreuses fonctionnalités mineures et corrections de bogues. Les [notes de version][0.18 notes] du projet décrivent tous les changements
  notables et listent chacune des 119 personnes dont les PR fusionnées ont aidé à contribuer à cette version. Parmi les fonctionnalités que
  nous pensons que les lecteurs de ce bulletin pourraient trouver particulièrement intéressantes, on trouve,

  - *Davantage d'outils PSBT et d'améliorations :* la précédente version majeure, 0.17, a introduit la prise en charge des Transactions
    Bitcoin Partiellement Signées (PSBT) [BIP174][] conçues pour aider plusieurs programmes ou appareils à créer et signer collaborativement
    des transactions, comme les portefeuilles multisig, les portefeuilles matériels et les portefeuilles à froid. La version 0.18 s'appuie
    sur cette base avec plusieurs corrections de bogues et améliorations, dont trois nouveaux RPC : `joinpsbts` pour fusionner ensemble
    plusieurs PSBT ; `analyzepsbt` pour indiquer à l'utilisateur ce qu'il doit faire ensuite avec la PSBT ; et `utxoupdatepsbt` pour ajouter
    les informations nécessaires à une PSBT à partir de l'ensemble UTXO d'un nœud. De plus, la section PSBT des notes de version de la 0.17
    a été placée dans un [document séparé][PSBT documentation] et étendue pour couvrir les nouvelles fonctionnalités ajoutées dans la 0.18.

  - *Prise en charge RPC initiale des descripteurs de script de sortie :* les logiciels Bitcoin ont besoin d'un moyen de trouver toutes les
    transactions sur la chaîne de blocs qui paient le portefeuille d'un utilisateur. C'est facile si le portefeuille ne prend en charge
    qu'un seul format de scriptPubKey---par ex., pour P2PKH, le portefeuille hache chacune de ses clés publiques et recherche tout
    scriptPubKey payant `0x76a9[hash160 de n'importe quelle clé publique du portefeuille]88ac`. Mais le portefeuille intégré de Bitcoin Core
    prend actuellement en charge de nombreux formats de scriptPubKey différents---P2PK, P2PKH, P2WPKH, multisig nu, engagements P2SH et
    engagements P2WSH. Cela offre de la flexibilité et une compatibilité descendante, mais au prix d'une mauvaise évolutivité : le
    portefeuille consomme du temps CPU à rechercher des scripts anciens ou rares que la plupart des utilisateurs n'utilisent jamais.

    Les [descripteurs de script de sortie][] sont un nouveau langage développé par Pieter Wuille pour décrire de façon concise les
    scriptPubKeys afin que le portefeuille sache exactement ce qu'il doit rechercher. L'objectif ultime est que le portefeuille de Bitcoin
    Core contienne une simple liste de descripteurs décrivant tous ses scripts---une liste qui peut être aussi courte qu'un seul descripteur
    pour la plupart des utilisateurs tout en prenant en charge une large flexibilité pour de futures mises à niveau et des cas d'utilisation
    avancés (y compris le multisig et la signature matérielle) ; voir les PR [#15487][Bitcoin Core
    #15487] et [#15764][Bitcoin Core #15764] pour le travail allant dans ce
    sens. Cependant, afin de permettre aux utilisateurs comme aux développeurs du projet d'acquérir de l'expérience avec les descripteurs
    avant que des changements fondamentaux ne soient apportés au portefeuille, la version 0.18 met à jour des RPC existants et ajoute de
    nouveaux RPC fonctionnant avec les descripteurs. Les RPC existants mis à jour avec la prise en charge des descripteurs incluent
    `scantxoutset`, `importmulti`, `getaddressinfo`, et `listunspent`. Les nouveaux RPC incluent `deriveaddresses` et `getdescriptorinfo`.

  - *Prise en charge basique des signataires matériels via un outil indépendant :* publié séparément de la 0.18, mais faisant toujours
    partie du projet Bitcoin Core, se trouve l'outil [Hardware Wallet Interaction][HWI] (HWI) qui permet aux utilisateurs à l'aise avec la
    ligne de commande d'utiliser Bitcoin Core avec plusieurs modèles populaires de portefeuilles matériels. En interne, l' outil fait un
    usage intensif des PSBT et des descripteurs de script de sortie, ce qui lui permet d'être intégré avec d'autres portefeuilles qui
    prennent en charge ces interfaces (par ex. la [prise en charge expérimentale de Wasabi wallet][wasabi hwi]). Le travail a déjà commencé
    pour intégrer plus directement HWI aux principaux outils de Bitcoin Core et construire des interfaces graphiques pour lui.

  - *Nouvel outil de portefeuille :* aux côtés de `bitcoind` et des autres programmes Bitcoin se trouve un nouvel outil `bitcoin-wallet`.
    Cet outil en ligne de commande permet actuellement seulement à l'utilisateur de créer un nouveau portefeuille ou d'effectuer quelques
    inspections de base sur un portefeuille existant, mais il est prévu d'ajouter davantage de fonctionnalités à l'outil dans les versions
    ultérieures.

  - *Nouvelle architecture et nouveau paquet Ubuntu Snap :* il s'agit de la première version à fournir des [binaires
    précompilés][bitcoincore.org download] pour Linux sur l'architecture CPU RISC-V. Pour les utilisateurs d'Ubuntu et des systèmes
    compatibles, cette version fournit également un [paquet Snap][] qui remplace le PPA qui était mis à jour dans les versions précédentes.
    Les paquets RISC-V et Snap incluent tous deux des binaires qui sont construits de manière déterministe et [signés][gitian sigs] par
    plusieurs contributeurs de Bitcoin Core.

    {% comment %}<!--
    152 Tests and QA 74 Docs 65 wallet 55 RPCs and other APIs 51 GUI 47 Build system 43 Misc 17 p2p and network code 13 Platform support 9
    block and tx handling 1 mining 1 consensus -->{% endcomment %}

  - *Nombreux changements dans les tests et l'Assurance Qualité (QA) :* les [notes de version][0.18 notes] listent toutes les PR liées à la
    0.18 que le responsable de publication de Bitcoin Core a jugées significatives, réparties en douze catégories. Bien que l'importance et
    les critères de catégorisation soient quelque peu arbitraires, et que le nombre de PR ne soit pas nécessairement corrélé à la quantité
    de travail effectuée, nous pensons qu'il est notable que la section "Tests and QA" des notes de version comporte plus du double du
    nombre de PR listées dans toute autre catégorie. Nous n'avons pas souvent l'occasion d'écrire sur les tests dans ce bulletin---les tests
    font rarement l'actualité sauf quand quelque chose tourne mal---nous voulions donc saisir cette occasion pour rappeler aux lecteurs que
    les tests restent une partie active et importante du développement de Bitcoin Core.

  - *Projet de passer par défaut aux adresses de réception bech32 :* comme mentionné dans la section *nouvelles* du [Bulletin #40][], les
    notes de version annoncent l'intention du projet de passer par défaut aux adresses d'envoi bech32 soit dans la prochaine version majeure
    (0.19, [prévue vers novembre 2019][0.19 release schedule]) soit dans la version suivante (prévue environ un an plus tard). La date la
    plus proche est la cible actuelle.

- **Proposition de prise en charge des signatures Schnorr et des engagements de script Taproot :** Pieter Wuille a [publié][tap post] sur la
  liste de diffusion Bitcoin-Dev un [BIP proposé pour Taproot][taproot] (utilisant des signatures Schnorr) et un [BIP proposé pour
  Tapscript][tapscript], une petite variation du langage Script actuel de Bitcoin à utiliser avec les charges Taproot. Est également fournie
  une [implémentation de référence][tap ref] des deux propositions qui réalise tous les changements de consensus en environ 520 lignes de
  code (à l'exclusion des changements liés aux signatures Schnorr qui seront ajoutés à la bibliothèque [libsecp256k1][] ; voir le
  [bip-schnorr][] publié précédemment pour plus d'informations).

  L'annonce des propositions est arrivée trop tard dans le processus de rédaction pour que nous puissions fournir une description détaillée
  dans ce bulletin, bien que nous ayons modifié un peu d'autre texte dans ce bulletin pour refléter la publication des propositions. Nous
  prévoyons de fournir une couverture complète la semaine prochaine.

## Prise en charge de l'envoi bech32

*8e semaine sur 24. Jusqu'au deuxième anniversaire du verrouillage du soft fork segwit le 24 août 2019, le Bulletin Optech contiendra cette
section hebdomadaire qui fournit des informations pour aider les développeurs et organisations à mettre en œuvre la prise en charge de
l'envoi bech32---la capacité de payer des adresses segwit natives. Cela [ne nécessite pas d'implémenter segwit][bech32 series] vous-même,
mais cela permet aux personnes que vous payez de profiter de l'ensemble des multiples avantages de segwit.*

{% comment %}<!-- weekly reminder for harding: check Bech32 Adoption
wiki page for changes -->{% endcomment %}

{% include specials/bech32/08-upgradability.md %}

## Changements notables dans le code et la documentation

*Changements notables cette semaine dans [Bitcoin Core][bitcoin core repo], [LND][lnd repo], [C-Lightning][c-lightning repo],
[Eclair][eclair repo], [libsecp256k1][libsecp256k1 repo], et [Bitcoin Improvement Proposals (BIPs)][bips repo].*

- [Bitcoin Core #15323][] met à jour le RPC `getmempoolinfo` et les points d'accès REST `/rest/mempool/info.json` afin qu'ils renvoient un
  champ `loaded` qui vaut *true* si le mempool sauvegardé a été entièrement chargé depuis le disque ou *false* s'il est encore en cours de
  chargement.

- [Bitcoin Core #15141][] prend le code qui bannit les pairs pour l'envoi de données invalides et le déplace du code de validation vers le
  code de gestion du réseau. Plus précisément, lorsque le code réseau transmet de nouvelles données au code de validation et que le code de
  validation les renvoie comme invalides, il renvoie également une raison de l'invalidité. Le code réseau peut utiliser cette raison pour
  déterminer si le pair qui a envoyé les données doit être banni, autrement pénalisé, ou pas pénalisé du tout (par ex. le pair a envoyé des
  données invalides parce qu'il exécute une version de nœud antérieure à un soft fork et n'a donc pas connaissance des nouvelles règles).
  Cela crée non seulement une séparation plus claire entre les couches dans le code du système, mais prépare également de futures
  améliorations du code de gestion des pairs qui lui permettront d'être plus intelligent pour bannir des pairs selon plusieurs critères.

{% comment %}<!-- This was direct pushed (no PR): https://github.com/lightningd/plugins/commit/187c66a9b1412edced3c51cb53ba568f245a5614 --> {% endcomment %}

- Le [dépôt de plugins C-Lightning][] a reçu un plugin [autopilot][cl autopilot] qui peut aider les utilisateurs à choisir un ou plusieurs
  canaux à ouvrir pour commencer à envoyer des paiements LN. Le plugin est basé sur une [PR antérieure][C-Lightning #1888] du dépôt
  principal de code de C-Lightning.

{% include linkers/issues.md issues="15487,15764,15323,15141,1888" %}
[0.18.0]: https://bitcoincore.org/bin/bitcoin-core-0.18.0/
[snap package]: https://snapcraft.io/bitcoin-core
[0.19 release schedule]: https://github.com/bitcoin/bitcoin/issues/15940
[c-lightning plugin repository]: https://github.com/lightningd/plugins
[cl autopilot]: https://github.com/lightningd/plugins/tree/master/autopilot
[0.18 notes]: https://bitcoincore.org/en/releases/0.18.0/
[psbt documentation]: https://github.com/bitcoin/bitcoin/blob/master/doc/psbt.md
[bitcoincore.org download]: https://bitcoincore.org/en/download/
[gitian sigs]: https://github.com/bitcoin-core/gitian.sigs
[wasabi hwi]: https://github.com/zkSNACKs/WalletWasabi/pull/1341
[tap post]: https://gnusha.org/url/https://lists.linuxfoundation.org/pipermail/bitcoin-dev/2019-May/016914.html
[taproot]: https://github.com/sipa/bips/blob/bip-schnorr/bip-taproot.mediawiki
[tapscript]: https://github.com/sipa/bips/blob/bip-schnorr/bip-tapscript.mediawiki
[tap ref]: https://github.com/sipa/bitcoin/commits/taproot
[bech32 series]: /en/bech32-sending-support/
[le bulletin #40]: /en/newsletters/2019/04/02/#bitcoin-core-schedules-switch-to-default-bech32-receiving-addresses
[output script descriptors]: https://github.com/bitcoin/bitcoin/blob/master/doc/descriptors.md
[hwi]: https://github.com/bitcoin-core/HWI
