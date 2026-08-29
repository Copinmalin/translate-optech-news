# translate-optech-news
Automate translation for Bitcoinops newsletter.

## Traduction hebdomadaire avec relecture

Le workflow `.github/workflows/weekly-latest-newsletter.yml` se lance chaque vendredi a 18:15 UTC, donc apres 18 h en France en heure d'hiver comme en heure d'ete. Il peut aussi etre lance manuellement.

Le workflow :

1. detecte la derniere newsletter publiee ;
2. ne fait rien si sa traduction est deja presente sur `Copinmalin/bitcoinops.github.io:master` ;
3. traduit la newsletter et repare ses liens internes ;
4. ouvre une PR brouillon dans ce depot et demande une relecture a `Copinmalin` ;
5. apres passage en **Ready for review** et review **Approve**, cree la branche `Newsletter-N-translate-in-French` dans le fork puis la PR vers `bitcoinops/bitcoinops.github.io:master` ;
6. ferme la PR de relecture sans la fusionner dans le depot d'outillage.

Secrets requis :

- `OPENAI_API_KEY` pour la traduction ;
- `BITCOINOPS_REPO_TOKEN`, un token donnant l'ecriture sur `Copinmalin/bitcoinops.github.io` et permettant de creer une PR vers le depot public amont.

Le token inter-depots n'est utilise qu'apres l'approbation humaine. Si le secret est absent, la preparation et la notification de relecture fonctionnent, mais la publication amont s'arrete avec un message explicite.

## Workflow mensuel automatique vers `bitcoinops.github.io`
Oui, c'est possible de tout chaîner automatiquement :
1. Sélectionner le plus ancien mois qui n'est pas encore complètement traduit.
2. Lancer la traduction des newsletters manquantes de ce mois.
3. Copier les fichiers FR dans un clone local de `Copinmalin/bitcoinops.github.io`.
4. Créer une branche + un commit avec le titre `Newsletter yyyy.mm translate in French`.
5. Afficher ou créer la PR GitHub.

Le script dédié est `scripts/sync_monthly_translation_pr.py`.

### Exemple (sélection automatique du mois)
```bash
python scripts/sync_monthly_translation_pr.py \
  --bitcoinops-repo /path/to/bitcoinops.github.io \
  --print-gh-pr
```

### Exemple (forcer un mois)
```bash
python scripts/sync_monthly_translation_pr.py \
  --bitcoinops-repo /path/to/bitcoinops.github.io \
  --month 2026-03 \
  --print-gh-pr
```

### Exemple (création directe de la PR)
```bash
python scripts/sync_monthly_translation_pr.py \
  --bitcoinops-repo /path/to/bitcoinops.github.io \
  --create-pr
```

### Notes
- Le script utilise `optech_fr.py` pour la traduction (requiert `OPENAI_API_KEY`).
- `--min-date` permet de limiter la période analysée.
- `--work-dir` permet d'isoler les fichiers générés pendant le workflow.


## GitHub Action
Un workflow GitHub Actions est disponible dans `.github/workflows/monthly-sync-pr.yml` pour lancer ce script depuis l'interface Actions.

Secrets requis :
- `OPENAI_API_KEY` : clé OpenAI pour la traduction.
- `BITCOINOPS_REPO_TOKEN` : token GitHub **nécessaire** pour push/PR cross-repo avec droits d'écriture sur `Copinmalin/bitcoinops.github.io`.  
  Sans ce secret, le workflow exécute la traduction/commit localement dans le job puis **ignore** le push/PR (warning explicite) pour éviter l'erreur 403.
