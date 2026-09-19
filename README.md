# translate-optech-news
Automate translation for Bitcoinops newsletter.

## Traduction hebdomadaire avec relecture

Le workflow `.github/workflows/weekly-latest-newsletter.yml` se lance chaque vendredi a 18:15 UTC, donc apres 18 h en France en heure d'hiver comme en heure d'ete. Il peut aussi etre lance manuellement.

Le workflow :

1. detecte la derniere newsletter publiee ;
2. ne fait rien si sa traduction est deja présente sur `bitcoinops/bitcoinops.github.io:master` ;
3. traduit la newsletter et repare ses liens internes ;
4. ouvre une PR brouillon dans ce depot et demande une relecture a `Copinmalin` ;
5. apres passage en **Ready for review** et review **Approve**, synchronise le `master` du fork avec l'amont, cree la branche `Newsletter-N-translate-in-French` depuis ce `master` à jour, revalide et rebase la branche si l'amont a avancé, exécute `make production`, puis ouvre la PR vers `bitcoinops/bitcoinops.github.io:master` uniquement si le contrôle réussit ;
6. ferme la PR de relecture sans la fusionner dans le depot d'outillage.

Secrets requis :

- `OPENAI_API_KEY` pour la traduction ;
- `BITCOINOPS_REPO_TOKEN`, un token donnant l'ecriture sur `Copinmalin/bitcoinops.github.io` et permettant de creer une PR vers le depot public amont.

Le token inter-depots n'est utilise qu'apres l'approbation humaine. Si le secret est absent, la preparation et la notification de relecture fonctionnent, mais la publication amont s'arrete avec un message explicite.

### Nettoyage des branches publiées

Le workflow `.github/workflows/cleanup-merged-newsletter-branches.yml` contrôle chaque jour les branches de relecture et de publication. Il supprime uniquement :

- une branche `Newsletter-N-translate-in-French` du fork lorsque sa PR vers `bitcoinops/bitcoinops.github.io:master` est fusionnée et que le fichier traduit est présent sur `master` ;
- la branche `review/newsletter-N-*` correspondante après la même double vérification et seulement si son fichier est identique à celui publié.

La branche du fork doit encore pointer sur le commit fusionné. Les PR amont ouvertes, fermées sans fusion, dont le fichier n'est pas publié sur `master`, ou les branches modifiées après publication sont conservées. Le lancement manuel est en simulation par défaut (`dry_run: true`). Le lancement planifié quotidien effectue le nettoyage réel.

## Rattrapage mensuel chaîné

Le workflow `.github/workflows/monthly-sync-pr.yml` traduit l'historique dans l'ordre, un mois à la fois :

1. il lit les newsletters anglaises et françaises depuis `bitcoinops/bitcoinops.github.io:master` ;
2. il tient compte des traductions déjà présentes dans des PR ouvertes ;
3. il sélectionne le plus ancien mois incomplet depuis la première newsletter, publiée le 8 juin 2018 ;
4. il traduit les newsletters manquantes du mois et applique la même réparation de liens que le workflow hebdomadaire ;
5. il ouvre une PR brouillon de relecture dans ce dépôt, assignée à `Copinmalin` ;
6. après passage en **Ready for review** et review **Approve**, il synchronise le `master` du fork avec l'amont, crée la branche mensuelle depuis ce `master` à jour, la rebase si l'amont a avancé, exécute `make production` et ouvre une PR vers `bitcoinops/bitcoinops.github.io:master` uniquement si le contrôle réussit ;
7. il ferme la PR de relecture puis déclenche automatiquement la préparation du mois incomplet suivant.

Une seule PR mensuelle de relecture peut être ouverte à la fois. La chaîne s'arrête naturellement quand toutes les newsletters sont traduites ou déjà couvertes par des PR ouvertes. Le lancement manuel permet de la démarrer ou de la reprendre. Le lancement planifié du premier jour du mois sert de filet de sécurité.

La synchronisation du fork est uniquement un fast-forward. Si son `master` contient des commits absents de Bitcoin Optech, la publication s'arrête explicitement au lieu de réécrire ou perdre ces commits.

Le préflight utilise Ruby 3.4, `optipng` et la commande `make production` définie par Bitcoin Optech, comme Travis CI. Il contrôle notamment le format Markdown, les métadonnées, les schémas, la construction Jekyll, les ancres et les liens internes avec HTML-Proofer. Le déploiement Netlify reste exécuté par Bitcoin Optech après ouverture de la PR, car il dépend de leur environnement hébergé.

Ne pas fusionner les PR de relecture dans le dépôt d'outillage. L'approbation humaine est la seule commande de publication et de progression vers le mois suivant.

Le script `scripts/sync_monthly_translation_pr.py` peut aussi préparer localement le plus ancien mois incomplet à partir d'un clone de l'amont :

```bash
python scripts/sync_monthly_translation_pr.py \
  --bitcoinops-repo /path/to/bitcoinops.github.io \
  --work-dir output/monthly-workflow
```

Options utiles :

- `--month YYYY-MM` force un mois précis ;
- `--min-date YYYY-MM-DD` change le début de la plage ;
- `--covered-slugs-file` exclut les fichiers déjà couverts par des PR ouvertes.

Secrets requis :

- `OPENAI_API_KEY` pour préparer les traductions ;
- `BITCOINOPS_REPO_TOKEN` uniquement après l'approbation, pour pousser dans `Copinmalin/bitcoinops.github.io` et ouvrir la PR amont.
