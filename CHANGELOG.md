# Changelog

Historique des versions du **Mandataire financier** (SCOPA), de la plus récente
à la plus ancienne. Ce fichier est la **source de vérité** : l'onglet
« À propos » de l'application en est généré (voir `scripts/changelog_to_json.py`).

Format d'une entrée : `## vX.Y.Z — <date ISO> — <titre>`, suivi de la liste des
changements décrits du point de vue de l'utilisateur. Une version `vX.0.0`
marque un palier majeur et s'affiche en évidence.

Historique reconstitué depuis l'historique Git du dépôt.

## v0.35.0 — 2026-10-04 — Une campagne neuve est utilisable immédiatement

### Corrigé
- Sur une campagne dont l'écran Identité n'avait jamais été enregistré, il était impossible d'enregistrer un emprunt ou de déposer un récépissé : l'opération échouait silencieusement. L'élection à laquelle tout se rattache n'existait pas encore en base. Elle naît désormais avec la campagne, et se crée au besoin sur les campagnes déjà dans cet état.
- Déposer un récépissé avant d'avoir saisi l'identité crée la fiche correspondante à vide. Ses champs restent signalés comme manquants : le dépôt d'une pièce ne fait pas croire l'identité renseignée.

## v0.34.1 — 2026-10-04 — Les sénatoriales dans les types de scrutin

### Corrigé
- Le type de scrutin « sénatoriale » manquait à la liste : une campagne sénatoriale devait se déclarer en « autre ». Signalé par deux bêta-testeurs.

## v0.34.0 — 2026-10-03 — Rapprocher une ligne au moment où on la saisit

### Ajouté
- Chaque ligne saisie propose une liste déroulante des dépenses — ou des recettes pour un encaissement — qu'il reste à rapprocher, avec leur numéro de pièce et le montant dû. Désigner l'écriture réglée rapproche la ligne aussitôt : plus besoin de la retrouver ensuite dans un autre écran.
- La liste est disponible aux trois endroits où l'on saisit des lignes : création d'un relevé, ajout sur un relevé existant, et « Reste à faire ».

### Sécurité
- Un décaissement ne peut pas alimenter une recette, ni un encaissement régler une dépense. Changer le sens d'une ligne efface l'écriture désignée.
- Le montant imputé ne dépasse jamais ce qui reste dû : une ligne plus grosse que la facture la solde sans plus, une ligne plus petite laisse la dépense ouverte pour un second versement.

## v0.33.0 — 2026-10-03 — Saisir un relevé depuis le « Reste à faire »

### Ajouté
- Les sections « Relevés bancaires » et « Rapprochement bancaire » permettent de saisir les lignes directement, sans quitter l'écran. Les autres manques se réglaient déjà sur place ; ceux-là renvoyaient vers un autre écran.

## v0.32.0 — 2026-10-03 — Saisie manuelle des transactions bancaires

### Ajouté
- Les lignes d'un relevé peuvent être saisies directement : date, libellé, numéro de chèque ou référence, sens et montant. Toutes les banques ne proposent pas un export exploitable, et reporter ce qu'on lit sur le relevé papier reste parfois le seul moyen. La saisie s'ajoute aux trois voies existantes — fichier CSV, copier-coller, PDF ou photo.
- Une ligne oubliée s'ajoute à un relevé déjà enregistré, et se retire si elle a été saisie en double. Retirer une ligne délie ce qu'elle réglait, pour qu'aucune dépense ne reste payée en pointant un mouvement disparu.

### Modifié
- Le relevé compte désormais deux fois dans le dossier : comme source des transactions, et comme pièce de l'enveloppe B. Des lignes saisies à la main sans le relevé scanné laissent le dossier incomplet — ce que rien ne signalait. Le document se dépose depuis le « Reste à faire » ou depuis l'écran des relevés.

## v0.31.0 — 2026-10-03 — Contrat de prêt exigé

### Ajouté
- Une recette enregistrée comme prêt doit porter son contrat écrit : le « Reste à faire » le signale et bloque le dépôt tant qu'il manque. Un prêt sans contrat ne se distingue pas d'un don déguisé.
- Déposer le contrat depuis cette ligne **crée l'emprunt** correspondant, en reprenant le prêteur, le montant et la date de la recette. Les deux vivaient jusqu'ici séparément : enregistrer un prêt en recette ne créait aucun emprunt, et l'onglet Emprunts était une saisie parallèle sans lien avec la comptabilité. Taux et durée restent facultatifs, à compléter dans cet onglet.
- L'onglet Emprunts indique si le contrat est présent, et permet de l'ouvrir. L'information existait en base sans jamais être affichée.

## v0.30.0 — 2026-10-03 — Les pièces ne sont plus accessibles sans session

### Sécurité
- Les justificatifs étaient servis comme des fichiers statiques : toute personne connaissant l'adresse d'une pièce pouvait l'ouvrir sans être connectée. Ces documents portent des noms et adresses de donateurs, des factures et des relevés bancaires. Ils passent désormais par un accès authentifié.
- Une pièce n'est servie qu'aux membres de la campagne à laquelle elle appartient. Le dossier des justificatifs étant commun à toutes les campagnes, une pièce d'un autre dossier était jusqu'ici lisible.

### Corrigé
- Le rapprochement bancaire compte dans le score même lorsqu'aucun relevé n'a été importé. Un dossier dont aucune écriture n'est rapprochée s'affichait à 95 % alors qu'il est loin d'être déposable. Sans relevé, le manque est énoncé en une ligne plutôt qu'écriture par écriture.

## v0.29.0 — 2026-10-03 — Supprimer une pièce la détache vraiment

### Corrigé
- Supprimer un justificatif n'effaçait que le fichier sur le disque. La pièce restait rattachée à son événement, à sa dépense ou à sa recette, et restait annoncée au bordereau : elle devenait une pièce fantôme que plus rien ne permettait de retirer, et qui bloquait le dépôt sans issue. La suppression retire désormais la pièce, tous ses rattachements, puis le fichier.
- Le fichier n'est effacé du disque que si aucune autre campagne ne s'en sert. Le dossier des justificatifs est commun à toutes les campagnes : un testeur ne doit pas pouvoir trouer celui d'un autre.

### Ajouté
- Une pièce dont le fichier a disparu apparaît désormais dans l'écran Justificatifs, signalée « Fichier introuvable ». Elle n'y figurait nulle part — l'écran ne listait que le disque — et restait donc impossible à corriger. Elle peut maintenant être redéposée ou supprimée.

## v0.28.0 — 2026-10-03 — Modification d'une recette

### Ajouté
- Une recette se modifie depuis sa liste, comme une dépense : un crayon ouvre le formulaire prérempli. Un prêt saisi par erreur en don se requalifie sans supprimer la ligne ni la ressaisir, et sa rubrique comptable suit le changement.

### Sécurité
- Requalifier un don pour lequel un reçu-don a été délivré est refusé : ce reçu porte un numéro de carnet remis au donateur, il doit être annulé avant. Un reçu déjà annulé ne bloque pas.
- Le suivi « reçu envoyé » est effacé quand une recette cesse d'être un don : il n'y a pas d'attestation fiscale sur un prêt.

## v0.27.0 — 2026-10-03 — Rapprochement bancaire des recettes, et exigé au dépôt

### Ajouté
- Les recettes se rapprochent du relevé bancaire, comme les dépenses le faisaient déjà. Une ligne au crédit s'affecte à une ou plusieurs recettes : une remise de chèques couvre souvent plusieurs dons, qui s'imputent un à un jusqu'à solder la ligne. Rien de tout cela n'existait côté encaissement.
- Le « Reste à faire » signale les dépenses et les recettes qu'aucun mouvement bancaire ne justifie encore. Une écriture que le relevé ne porte pas est précisément ce que la commission cherche. Les concours en nature en sont exclus : ils ne passent pas par le compte.

### Corrigé
- Supprimer un relevé remet les recettes qu'il justifiait à l'état non rapproché, au lieu de les laisser pointer un relevé disparu. Les dépenses l'étaient déjà.

## v0.26.0 — 2026-10-03 — Événements récurrents

### Ajouté
- Un événement peut se répéter sur plusieurs dates : un tractage tous les samedis, une série de collages. Le formulaire propose un générateur — « chaque samedi, du 1er au 30 septembre » — qui remplit la liste des dates, puis chaque date se retire ou s'ajoute à la main. Le samedi où il pleuvait se supprime d'un clic.
- Chaque date retenue devient un événement à part entière : une dépense se rattache à l'occurrence précise qui la justifie, et le calendrier comme la frise les affichent individuellement.

## v0.25.0 — 2026-10-03 — Rattachement des dépenses aux événements

### Ajouté
- Le « Reste à faire » signale les dépenses qui ne sont rattachées à aucun événement, et permet de les rattacher sur place en choisissant dans la liste. Presque toute dépense relève d'un moment de campagne — même la colle d'un collage.
- Une dépense peut être déclarée « hors événement », depuis la même liste ou depuis son formulaire. C'est un arbitrage, pas un oubli : sans lui, une dépense sans rattachement resterait signalée indéfiniment.

## v0.24.0 — 2026-09-30 — Le mandataire s'affiche sur l'écran de choix

### Modifié
- Chaque carte de campagne indique désormais son mandataire financier, à la place de la mention « Mandat en cours • 2026 » qui était écrite en dur, année comprise. Rien n'interdit à deux campagnes de porter le même nom : c'est ce repère qui permet de les distinguer, notamment pour un administrateur qui les voit toutes.

## v0.23.0 — 2026-09-29 — Déconnexion depuis l'écran de choix des campagnes

### Ajouté
- Un bouton « Se déconnecter » sur l'écran de sélection des campagnes, avec le nom du compte connecté. Le bouton n'existait que dans la barre latérale, qui n'apparaît qu'une fois une campagne ouverte : il fallait donc entrer dans une campagne pour pouvoir sortir.

## v0.22.0 — 2026-09-29 — Onglet « Reste à faire »

### Ajouté
- Un onglet « Reste à faire », dans le groupe Conformité & dépôt, réunit tout ce qui manque avant de pouvoir déposer le compte. Ce qui se règle par un fichier — facture d'une dépense, justificatif d'une recette, récépissé de préfecture — se dépose directement sur la ligne concernée, identifiée par son numéro de pièce, son tiers et son montant. Le reste renvoie d'un clic à l'écran de saisie.

### Modifié
- Le bandeau « Dossier de dépôt incomplet » du tableau de bord et le bandeau « Export impossible » de l'écran Dépôt mènent désormais à cet onglet. Le premier renvoyait vers Identité, qui ne couvre qu'une partie des manques.

## v0.21.0 — 2026-09-29 — Les justificatifs manquants dans le score de complétude

### Ajouté
- Les dépenses et les recettes sans justificatif comptent désormais dans le pourcentage de complétude du dossier. Chaque manque est listé par son numéro de pièce et son montant, dans la barre du tableau de bord comme dans l'écran Dépôt : c'est la liste de ce qui reste à réunir avant de pouvoir déposer.
- Une recette peut recevoir sa pièce justificative — reçu-don, bordereau de remise, contrat de prêt — depuis la liste des recettes. La colonne du même nom ouvre la pièce quand elle existe, propose de la déposer sinon.

### Modifié
- Un concours en nature n'est pas compté comme dépense sans facture : c'est une prestation donnée, pas achetée. Même règle que la checklist de conformité.
- Une dépense ou une recette en attente de validation n'entre pas encore dans le décompte : elle n'est une étape du dossier qu'une fois acceptée par le mandataire.

## v0.20.0 — 2026-09-29 — Rattachement d'une dépense depuis son formulaire

### Ajouté
- Une dépense se rattache à un événement directement depuis son formulaire, à l'enregistrement comme à la modification, avec sa quote-part. Il fallait jusqu'ici ouvrir l'événement et y chercher la dépense. Une dépense ventilée entre plusieurs événements reste possible, la somme des quote-parts ne pouvant dépasser 100 %.

### Corrigé
- Le coût d'un événement additionnait les dépenses en attente de validation. Une dépense déposée par l'équipe ou l'expert-comptable ne déplace plus le coût affiché avant l'arbitrage du mandataire, comme partout ailleurs dans l'application.

## v0.19.0 — 2026-09-27 — Modification d'un événement

### Ajouté
- Un événement peut être modifié : titre, type, lieu, dates et description. Le formulaire s'ouvre prérempli depuis le crayon sur la carte de l'événement. Le serveur acceptait déjà la modification, mais aucun bouton ne la déclenchait.

### Corrigé
- L'équipe de campagne et la direction voyaient les boutons « Nouvel événement » et « Supprimer », réservés au mandataire : ils ne pouvaient que renvoyer une erreur. Ces actions ne s'affichent plus qu'au mandataire.

## v0.18.0 — 2026-09-25 — Numérotation des pièces comptables

### Ajouté
- Chaque dépense et chaque recette porte désormais un numéro de pièce (`D001`, `R001`), attribué à son enregistrement et visible dans les tableaux Dépenses, Recettes et dans la main courante. La colonne « N° pièce » existait déjà partout mais restait vide : rien ne l'avait jamais remplie.
- Les justificatifs du dossier exporté sont nommés et classés d'après le numéro de l'écriture qu'ils justifient (`Enveloppe_A/D001_facture.pdf`). Une ligne du journal se retrouve dans l'enveloppe sans avoir à la chercher. Les pièces déclaratives, qui ne sont pas des écritures, conservent leur rang dans l'enveloppe.
- Les écritures déjà saisies ont été numérotées dans l'ordre chronologique, celui du journal.

### Modifié
- Les pièces de l'enveloppe sortent dans l'ordre du bordereau, et non plus dans l'ordre où elles ont été versées.

## v0.17.2 — 2026-09-25 — Démarrage local sans conflit de ports

### Corrigé
- Le lancement local échouait silencieusement quand un autre projet occupait déjà les ports 8000 et 5173 : le backend ne démarrait pas, le frontend basculait sur un autre port, et l'application appelait l'API du projet voisin. La connexion échouait alors sans explication. Le script utilise des ports propres au projet, refuse de démarrer si l'un est pris — en nommant le processus fautif — et transmet lui-même l'adresse de l'API et l'origine autorisée.

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
