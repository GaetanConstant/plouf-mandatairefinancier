# Changelog

Historique des versions du **Mandataire financier** (SCOPA), de la plus récente
à la plus ancienne. Ce fichier est la **source de vérité** : l'onglet
« À propos » de l'application en est généré (voir `scripts/changelog_to_json.py`).

Format d'une entrée : `## vX.Y.Z — <date ISO> — <titre>`, suivi de la liste des
changements décrits du point de vue de l'utilisateur. Une version `vX.0.0`
marque un palier majeur et s'affiche en évidence.

Historique reconstitué depuis l'historique Git du dépôt.

## v0.17.1 — 2026-09-25 — Correctifs du rapprochement bancaire

### Corrigé
- Supprimer un relevé laissait ses dépenses marquées « payées » et « rapprochées », en pointant un relevé qui n'existait plus : la trésorerie comptait un décaissement sans ligne bancaire derrière.
- Une ligne au crédit pouvait régler une dépense. Un encaissement est une recette : le rapprochement aux dépenses ne concerne plus que les débits, et le compteur « à rapprocher » ne compte plus les crédits.
- L'écran Dépôt affichait « Export impossible » et « Prêt à déposer » côte à côte. Le second ne parle que des motifs de rejet et le dit désormais.
- La navigation débordait sur un écran de 720 pixels dès qu'un groupe de six entrées s'ouvrait. Elle tient maintenant sans défilement.
- L'accord exprès du mandataire, facultatif au dépôt, s'affichait comme « manquant » au même titre que les deux récépissés exigés.

## v0.17.0 — 2026-09-25 — Mise en conformité avec le guide du mandataire

- **Concours en nature** : un écran dédié les déclare avec leur origine — candidat, formation politique ou tiers personne physique —, leur nature, leur valeur et la méthode d'évaluation. Ils alimentent les annexes 4 et 4.1 du compte, et consomment le plafond légal sans toucher la trésorerie.
- **Prise en charge des dépenses** : une dépense indique si elle est réglée par le mandataire ou directement par un parti. L'export produit la ventilation verticale qu'attend le formulaire.
- **Classement des pièces** : les justificatifs sortent désormais dans l'ordre de la nomenclature comptable, et non plus par date d'ajout. Un dossier rendu dans l'ancien ordre était à reclasser à la main.
- **Relevés bancaires au dossier** : le fichier importé devient une pièce de l'enveloppe B, où le guide l'exige. Son absence bloque désormais l'export.
- **Pièces déclaratives** : les récépissés de candidature et de déclaration du mandataire se déposent depuis l'écran Identité et sont exigés au dépôt.
- **Dévolution de l'excédent** : l'écran Dépôt calcule l'excédent, dit s'il provient de l'apport personnel — auquel cas rien n'est dû — ou de financements extérieurs, et permet de consigner la décision.

## v0.16.0 — 2026-09-25 — Relevés bancaires et rapprochement

- Import d'un relevé bancaire de trois façons : fichier CSV de la banque, copier-coller des lignes, ou photo et PDF reconnus par OCR. Les transactions lues s'affichent en aperçu, à relire avant d'enregistrer.
- Chaque ligne du relevé se rapproche des dépenses qu'elle règle : une ligne peut en régler plusieurs, et une dépense peut être payée en plusieurs fois, acompte puis solde.
- Les montants sont contrôlés : aucune imputation ne peut dépasser le montant de la transaction ni le TTC de la dépense.
- Les lignes sans dépense en face — frais bancaires, encaissement d'un don — restent au relevé et sont signalées.
- Une dépense intégralement rapprochée passe automatiquement en « payée ».
- La main courante montre désormais la date de facture, la date de paiement, le libellé de la dépense et celui du relevé.

### Modifié
- La date portée par une dépense s'appelle désormais « date de facture » : elle en a toujours été une, mais son ancien nom laissait croire à une date de règlement.

## v0.15.2 — 2026-09-24 — Utilisable sur téléphone

### Corrigé
- Le menu occupait 256 pixels fixes : sur un téléphone, il ne restait qu'une centaine de pixels au contenu. Il devient un tiroir, ouvert par un bouton et refermé dès qu'on navigue.
- Les tableaux trop larges faisaient déborder la page entière ; ils défilent désormais dans leur cadre, et les dates ne se coupent plus sur trois lignes.
- Les formulaires à deux colonnes s'empilent sous 640 pixels, les en-têtes passent à la ligne au lieu d'écraser leur titre, et les marges s'ajustent à la taille de l'écran.

## v0.15.1 — 2026-09-24 — Dépôt de justificatif par la direction

### Ajouté
- La direction de campagne et l'équipe peuvent verser un justificatif sur une dépense existante, sans pouvoir en modifier le moindre champ. La pièce part à la validation du mandataire.

### Corrigé
- L'équipe de campagne ne pouvait pas déposer de dépense : le bouton existait mais l'API refusait l'appel.
- Une pièce en attente de validation s'affichait déjà comme justificatif de la dépense.

## v0.15.0 — 2026-09-24 — Direction de campagne

- Nouveau rôle « direction de campagne » : il lit la comptabilité — tableau de bord, plafond, dépenses, justificatifs, conformité, main courante — et dépose comme l'équipe, sous validation du mandataire.
- La direction ne voit pas l'identité des donateurs : l'écran des recettes lui est fermé, et les noms sont remplacés par une mention neutre dans la main courante et les alertes de conformité. Un don politique est une donnée personnelle sensible.
- La page de connexion propose « totoenvacances » en exemple d'identifiant, comme les autres applications Plouf.

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
