# Changelog

Historique des versions du **Mandataire financier** (SCOPA), de la plus récente
à la plus ancienne. Ce fichier est la **source de vérité** : l'onglet
« À propos » de l'application en est généré (voir `scripts/changelog_to_json.py`).

Format d'une entrée : `## vX.Y.Z — <date ISO> — <titre>`, suivi de la liste des
changements décrits du point de vue de l'utilisateur. Une version `vX.0.0`
marque un palier majeur et s'affiche en évidence.

Historique reconstitué depuis l'historique Git du dépôt.

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
