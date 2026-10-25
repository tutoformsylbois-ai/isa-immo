# ISA Immo

Application qui rassemble les maisons **à vendre** et **à louer** de plusieurs sites d'annonces,
pour un suivi professionnel du marché. Même fonctionnement que « Maisons d'Argenton », avec des secteurs plus larges.

## Secteurs

| Secteur | Communes |
|---|---|
| Argenton-sur-Creuse | la commune seule |
| Argenton 10 km | à moins de 10 km d'Argenton |
| Argenton 10 à 20 km | entre 10 et 20 km d'Argenton |
| Argenton 20 à 30 km | entre 20 et 30 km d'Argenton |
| Azerables (10 km) | à moins de 10 km d'Azerables (23160) |
| Liglet (10 km) | à moins de 10 km de Liglet (86290) |

Les couronnes autour d'Argenton ne se chevauchent pas ; une commune peut en revanche être à la fois dans
« Argenton 20 à 30 km » et dans « Azerables ».
Couleurs des filtres : rouge pour les secteurs d'Argenton, vert pour Azerables, bleu pour Liglet ; chaque fiche porte aussi l'étiquette colorée de son ou ses secteurs. La liste (103 communes, Indre, Creuse, Vienne et Haute-Vienne) est dans
`data/communes.json`. Pour changer les secteurs : modifier `CENTRES` / `COURONNES` dans `maisons/communes.py`,
puis lancer `py outils/generer_communes.py` et `py outils/zones_bienici.py`.

## Utilisation

- **Ouvrir l'application** : double-cliquer sur `ouvrir_application.bat`. La page s'ouvre dans le navigateur (http://localhost:5000).
- **Mettre à jour les annonces** : bouton en haut de la page, ou `lancer_collecte.bat`.
  Une collecte prend 15 à 25 minutes : les dix sites sont interrogés en même temps, mais chacun lentement (une page toutes
  les 1,5 s, 4 s pour SeLoger) pour ne pas les surcharger.
- **Filtres** : prix, surface, **terrain minimum et maximum**, chambres, **DPE** (une ou plusieurs lettres ;
  la case « avec DPE non indiqué » garde ou écarte les maisons dont le site ne donne pas le DPE — iad, SAFTI,
  notaires, Zimo, PAP et Entreparticuliers ne l'indiquent pas sur leurs listes), commune, type de vendeur (agence, mandataire,
  notaire, particulier), agence ou conseiller précis ; tri par prix, prix au m², taille du terrain ou distance.
- **Agences et vendeurs du secteur** (en bas de page) : tous les professionnels qui ont au moins une maison en ligne
  dans les secteurs, avec le nombre d'annonces, les communes et les coordonnées quand le site les donne.
  Le bouton « Ses annonces » affiche ses biens.
- **Récapitulatif** : nouvelles annonces et baisses de prix depuis la mise à jour précédente, ou sur 7 ou 30 jours ;
  « Envoyer par e-mail » ouvre la messagerie avec le texte prêt.

## Sites collectés

Seuls les sites qui autorisent les robots sur leurs pages d'annonces (fichier robots.txt) et ne les bloquent pas sont collectés.

| Site | Contenu |
|---|---|
| Lesiteimmo | Agences locales, réseaux (iad, SAFTI…) et notaires |
| ParuVendu | Agences et particuliers |
| Bien'ici | Agences et mandataires de tous les réseaux |
| SeLoger | Agences, réseaux et quelques particuliers (avec adresse et téléphone du vendeur) |
| iad | Mandataires iad |
| SAFTI | Mandataires SAFTI |
| Notaires | immobilier.notaires.fr, offices notariaux de l'Indre, de la Creuse, de la Vienne et de la Haute-Vienne |
| Zimo | Agences et particuliers, dont des particuliers repris de Leboncoin |
| Entreparticuliers | Surtout des particuliers |
| PAP | Particuliers uniquement |

Écartés : Leboncoin, Superimmo (anti-robot), Figaro Immobilier, Ouest-France Immo (accès refusé),
Green-Acres, Logic-Immo, Century 21, Orpi, Etreproprio (pages d'annonces interdites dans robots.txt),
Capifrance, Propriétés-Privées, Square Habitat (anti-robot ; leurs biens paraissent en général sur SeLoger ou Bien'ici).
La liste est aussi affichée en bas de la page et se modifie dans `maisons/sources/__init__.py`.

Si un site bloque en cours de collecte (SeLoger le fait parfois), ce qui a été lu est gardé et aucune de ses annonces
n'est marquée comme retirée.

Un même bien publié sur plusieurs sites n'apparaît qu'une fois (même commune, même surface, même nombre de pièces) ;
la fiche donne alors tous les liens. Les offres de constructeurs (« maison à construire ») sont ignorées.

## Version en ligne (Netlify + GitHub), comme pour Maisons d'Argenton

- GitHub Actions (`.github/workflows/collecte.yml`) collecte chaque matin vers 7 h et à la demande,
  puis enregistre `data/annonces.db` et `site/index.html` ; Netlify remet le site en ligne.
- Le bouton « Mettre à jour » appelle `netlify/functions/mettre-a-jour.mjs`, qui lance la collecte sur GitHub.
- Variables Netlify : `GITHUB_TOKEN` (clé GitHub autorisée à lancer les « Actions » du dépôt) et `GITHUB_REPO` (`compte/depot`).

## Fichiers

- `collecte.py` : collecte les annonces et les enregistre dans `data/annonces.db`.
- `exporter_page.py` : fabrique la page (`--netlify` pour `site/index.html`) ; `publication/modele.html` en est le modèle.
- `app.py` : l'application locale (même page, plus le bouton de collecte).
- `maisons/sources/` : un fichier par site collecté.
- `maisons/communes.py` : les secteurs ; `data/communes.json` : leurs communes.
