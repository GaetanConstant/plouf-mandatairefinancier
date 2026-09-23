# Changelog

Historique des versions du **Mandataire financier** (SCOPA), de la plus récente
à la plus ancienne. Ce fichier est la **source de vérité** : l'onglet
« À propos » de l'application en est généré (voir `scripts/changelog_to_json.py`).

Format d'une entrée : `## vX.Y.Z — <date ISO> — <titre>`, suivi de la liste des
changements décrits du point de vue de l'utilisateur. Une version `vX.0.0`
marque un palier majeur et s'affiche en évidence.

Historique reconstitué depuis l'historique Git du dépôt.

## v0.14.1 — 2026-09-23 — Correction du chargement sans fin

### Corrigé
- L'application restait sur « Chargement des données » en boucle pour un rôle sans accès au tableau de bord : les chiffres du compte étaient réclamés puis refusés, indéfiniment.
- Un échec de chargement des chiffres affiche désormais sa raison au lieu d'un voile permanent.
- Une session expirée ramène à la page de connexion, au lieu de faire échouer chaque écran séparément.
- Page de connexion : les identifiants saisis étaient blancs sur fond blanc en mode sombre.

### Modifié
- Page de connexion aux couleurs de la France Insoumise.

## v0.14.0 — 2026-09-23 — Rôles et validation des contributions

- Trois rôles par campagne : mandataire, expert-comptable, équipe de campagne. Un même compte peut être mandataire d'une campagne et militant sur une autre.
- L'équipe et l'expert-comptable peuvent déposer dépenses, événements et pièces : rien n'entre dans le compte — plafond, trésorerie, exports, dossier de dépôt — avant validation du mandataire.
- Un écran « À valider » liste ce qui attend un arbitrage, avec l'auteur et la date de chaque dépôt ; une pastille dans le menu et un bandeau au tableau de bord préviennent à la connexion.
- Un refus ne supprime rien : son auteur retrouve l'élément avec le motif, le corrige et le soumet à nouveau.
- L'expert-comptable peut réclamer un justificatif manquant, auquel le mandataire répond.
- Le mandataire ouvre et retire les accès de sa campagne, rôle par rôle.
- Sécurité : les autorisations descendent dans l'API. Elles n'existaient que dans l'interface — masquer un écran n'empêchait pas d'appeler la route.

## v0.13.0 — 2026-09-23 — Calendrier de campagne

- Un écran Calendrier reconstruit le rétro-planning de la campagne : une ligne par activité, une case par semaine, de l'ouverture de la période de financement au jour du scrutin.
- Les longues plages sans activité sont repliées : la campagne réelle occupe la largeur utile, au lieu d'être écrasée par les mois vides de la période légale.
- Chaque activité porte son coût réel, repris du compte — il ne peut pas diverger.
- Le calendrier s'exporte en PDF et part automatiquement en annexe du dossier (enveloppe B), régénéré à chaque export.
- Photos et factures d'un événement remontent dans la chronologie et dans le dossier.
- Correction : la génération des conventions de mutualisation échouait sur macOS, faute de trouver les bibliothèques Pango installées par Homebrew.

## v0.12.0 — 2026-09-23 — Complétude du dossier et export des enveloppes

- Un score de complétude indique, section par section, ce qui manque avant de pouvoir déposer ; les zones incomplètes ressortent en rouge sur le tableau de bord, l'écran Identité et l'écran Dépôt.
- L'export des pièces officielles est refusé tant que le dossier est incomplet, avec la liste des manques.
- Le dossier s'exporte en entier : archive ZIP classée par enveloppe, ou PDF unique paginé avec les pièces à la suite du bordereau.
- Photos, factures et contrats se rattachent à un événement ; les photos rejoignent les annexes (enveloppe B).
- La chronologie affiche les photos de chaque événement.
- Les alertes de conformité deviennent cliquables : elles mènent directement à l'endroit où corriger — la dépense s'ouvre en modification, la recette est surlignée, la section d'identité amenée à l'écran.
- Une pièce annoncée au bordereau dont le fichier a disparu empêche désormais le dépôt.
- Un dossier sans aucun expert-comptable déclenche enfin une alerte : la règle ne se déclenchait que si une fiche existait déjà.

## v0.10.0 — 2026-09-22 — Devis, factures et pièces orphelines

- Une pièce jointe à une dépense se déclare comme devis ou comme facture, et se remplace quand le devis devient facture.
- Le fichier remplacé est effacé du disque, sauf s'il sert encore à une autre dépense.
- L'écran Justificatifs signale les fichiers rattachés à aucune dépense, à nettoyer avant l'envoi du dossier.

## v0.9.0 — 2026-09-22 — Versionnage et corrections de saisie

- Une dépense déjà enregistrée peut être corrigée : date, fournisseur, montant, imputation et statut.
- Le fournisseur se choisit dans la liste de ceux déjà saisis, avec création explicite d'un nouveau.
- Le tableau de bord affiche le plafond réel de l'élection en cours, et non plus une valeur figée.
- La page de connexion reprend la charte Plouf et affiche la version courante.
- Ajout de cet onglet À propos, qui retrace l'historique des versions.

## v0.8.0 — 2026-08-12 — Grands électeurs sénatoriaux

- Croisement des grands électeurs sénatoriaux du Rhône avec la liste électorale, coordonnées comprises.

## v0.7.0 — 2026-06-30 — Compte de campagne au format CNCCFP

- Export du compte de campagne au format officiel attendu par la commission.
- Annexes colistiers, équipe et emprunts, et journal des opérations enrichi.

## v0.6.0 — 2026-06-30 — Dépôt du compte

- Classement des pièces en enveloppes A et B, et génération du bordereau de dépôt.
- Conventions de mutualisation et livre de comptes de l'expert-comptable.

## v0.5.0 — 2026-06-30 — Pilotage de campagne

- Événements, frise chronologique, échéancier et rapport de campagne.
- Menu principal regroupé en blocs dépliables.

## v0.4.0 — 2026-06-29 — Conformité et identité administrative

- Moteur de règles de conformité avec page dédiée et checklist.
- Main courante : journal chronologique de l'annexe 8, exportable en Excel.

## v0.3.0 — 2026-06-29 — Reçus-dons numérotés

- Carnets de reçus-dons et délivrance numérotée conforme à la réglementation.

## v0.2.0 — 2026-06-29 — Socle de données durable

- Passage à une base par campagne, avec migrations versionnées.
- Sortie des secrets OwnCloud du code et durcissement de l'API.

## v0.1.0 — 2026-02-05 — Création de l'application

- Suivi des recettes, des dépenses et des concours en nature d'une campagne.
- Génération des reçus fiscaux signés et suivi des envois aux donateurs.
