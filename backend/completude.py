"""Complétude administrative du dossier de dépôt.

À distinguer du moteur de `conformite` : celui-ci vérifie des **règles** (dons
en espèces, plafonds, reçus), celui-là constate des **champs vides**. Un dossier
peut être parfaitement conforme et pourtant impossible à déposer parce que
l'expert-comptable n'est pas renseigné.

Le résultat alimente trois usages : la barre du tableau de bord, le détail par
section de l'écran Identité, et le refus d'export du dossier officiel.
"""

from __future__ import annotations

from typing import Callable, Optional

from sqlalchemy import select

from db.models import (
    Candidat,
    Colistier,
    CompteBancaire,
    Depense,
    Election,
    Emprunt,
    EvenementDepense,
    ExpertComptable,
    Mandataire,
    Recette,
)
from db.helpers import valides as _valides
from db.session import campaign_session, ensure_campaign_db
from db import enums


# Champs exigés pour un dépôt, par section : (attribut, libellé affiché).
# Les champs facultatifs (nom d'usage, libellé de compte, second tour…) n'y
# figurent pas : ils ne doivent pas faire baisser le score.
CHAMPS_ELECTION = [
    ("type", "Type de scrutin"),
    ("libelle", "Libellé"),
    ("circonscription", "Circonscription"),
    ("nuance_politique", "Nuance politique / Parti"),
    ("date_tour1", "Date du 1er tour"),
    ("plafond_depenses", "Plafond de dépenses"),
]

CHAMPS_CANDIDAT = [
    ("civilite", "Civilité"),
    ("nom", "Nom"),
    ("prenom", "Prénom"),
    ("date_naissance", "Date de naissance"),
    ("lieu_naissance", "Lieu de naissance"),
    ("adresse_postale", "Adresse postale"),
    ("code_postal", "Code postal"),
    ("ville", "Ville"),
    ("email", "Email"),
    ("tel", "Téléphone"),
]

CHAMPS_MANDATAIRE = [
    ("civilite", "Civilité"),
    ("nom", "Nom"),
    ("prenom", "Prénom"),
    ("adresse_postale", "Adresse postale"),
    ("code_postal", "Code postal"),
    ("ville", "Ville"),
    ("email", "Email"),
    ("tel", "Téléphone"),
    ("prefecture", "Préfecture de déclaration"),
    ("date_declaration_prefecture", "Date de déclaration en préfecture"),
    ("incompatibilites_verifiees", "Incompatibilités vérifiées"),
    ("capacite_civile_ok", "Capacité civile vérifiée"),
]

CHAMPS_EXPERT = [
    ("nom", "Nom de l'expert-comptable"),
    ("cabinet", "Cabinet"),
    ("adresse_postale", "Adresse postale"),
    ("date_designation", "Date de désignation"),
]

_CATEGORIE_RECETTE = {
    enums.CategorieRecette.don: "Don",
    enums.CategorieRecette.apport_perso: "Apport personnel",
    enums.CategorieRecette.pret: "Prêt",
    enums.CategorieRecette.contribution_parti: "Contribution d'un parti",
    enums.CategorieRecette.produit_divers: "Produit divers",
    enums.CategorieRecette.collecte: "Collecte",
}

CHAMPS_COMPTE = [
    ("banque", "Banque"),
    ("iban", "IBAN"),
    ("date_ouverture", "Date d'ouverture"),
]


def _rempli(valeur) -> bool:
    """Un booléen à False compte comme non rempli : ces cases sont des attestations."""
    if valeur is None:
        return False
    if isinstance(valeur, bool):
        return valeur
    if isinstance(valeur, str):
        return valeur.strip() != ""
    return True


def _evaluer_objet(obj, champs: list[tuple[str, str]]) -> tuple[int, list[str]]:
    """Nombre de champs remplis et libellés des manquants."""
    if obj is None:
        return 0, [libelle for _, libelle in champs]
    manquants = [libelle for attr, libelle in champs if not _rempli(getattr(obj, attr, None))]
    return len(champs) - len(manquants), manquants


def _section(cle: str, titre: str, total: int, remplis: int, manquants: list[str],
             note: Optional[str] = None, actions: Optional[list[dict]] = None) -> dict:
    """Une section du dossier.

    `manquants` énonce ce qui manque ; `actions` dit **où le corriger**. Les
    deux vont de pair : une liste de manques qu'on ne peut pas traiter depuis
    l'écran qui les affiche n'est qu'un constat.
    """
    return {
        "cle": cle,
        "titre": titre,
        "requis": total,
        "remplis": remplis,
        "manquants": manquants,
        "actions": actions or [],
        "pct": round(remplis / total * 100) if total else 100,
        "complet": not manquants,
        "note": note,
    }


def _vers_ecran(onglet: str, libelle: str, cible: Optional[str] = None) -> dict:
    """Action « aller corriger ailleurs », pour ce qui ne se règle pas par un fichier."""
    return {"type": "ecran", "onglet": onglet, "cible": cible, "libelle": libelle}


def _section_liste(colistiers: list[Colistier]) -> dict:
    """La liste des candidats : présence, rangs continus, alternance des sexes.

    L'alternance se lit sur la civilité, seule marque du sexe dans le modèle.
    """
    manquants: list[str] = []
    if not colistiers:
        return _section("liste", "Liste des candidats", 3, 0,
                        ["Aucun candidat saisi", "Rangs de la liste", "Alternance femme / homme"],
                        actions=[_vers_ecran("listeequipe", "Saisir dans Liste & équipe")])

    ordres = [c.ordre for c in colistiers]
    if any(o is None for o in ordres):
        manquants.append("Rang manquant sur au moins un candidat")
    else:
        attendus = list(range(1, len(colistiers) + 1))
        if sorted(ordres) != attendus:
            manquants.append("Rangs non continus à partir de 1")

    ordonnes = sorted((c for c in colistiers if c.ordre is not None), key=lambda c: c.ordre)
    civilites = [(c.civilite or "").strip().lower() for c in ordonnes]
    if any(not c for c in civilites):
        manquants.append("Civilité manquante sur au moins un candidat")
    elif any(a == b for a, b in zip(civilites, civilites[1:])):
        manquants.append("Alternance femme / homme rompue")

    return _section("liste", "Liste des candidats", 3, 3 - len(manquants), manquants,
                    note=f"{len(colistiers)} candidats",
                    actions=[_vers_ecran("listeequipe", "Corriger dans Liste & équipe")])


def _libelle_ecriture(num_piece: Optional[str], intitule: Optional[str],
                      montant: Optional[float], defaut: str) -> str:
    """Ligne actionnable : le numéro de pièce d'abord, c'est par lui qu'on classe."""
    repere = f"{num_piece} — " if num_piece else ""
    return f"{repere}{intitule or defaut} ({(montant or 0):.0f} €)"


def _section_justificatifs_depenses(s) -> dict:
    """Dépenses validées sans facture au dossier.

    Un concours en nature n'a pas de facture — c'est une prestation donnée, pas
    achetée. Même exception que le moteur de conformité, pour que les deux
    modules ne se contredisent pas.
    """
    depenses = [d for d in s.scalars(_valides(select(Depense), Depense)
                                     .order_by(Depense.num_piece)).all()
                if d.statut != enums.StatutDepense.realise_nature]
    sans_piece = [d for d in depenses if not d.facture_doc_id]
    manquants = [_libelle_ecriture(d.num_piece, d.nature, d.montant_ttc, "dépense")
                 for d in sans_piece]
    actions = [{"type": "depense", "id": d.id, "num_piece": d.num_piece,
                "libelle": d.nature or "dépense", "tiers": d.fournisseur,
                "montant": d.montant_ttc} for d in sans_piece]
    total = len(depenses)
    return _section(
        "justificatifs_depenses", "Justificatifs de dépenses", total,
        total - len(manquants), manquants, actions=actions,
        note=f"{total - len(manquants)}/{total} dépenses justifiées" if total else
             "Aucune dépense enregistrée",
    )


def _section_contrats_pret(s) -> dict:
    """Prêts sans contrat écrit au dossier.

    Un prêt se prouve par un contrat : c'est une pièce exigée, et sans elle la
    recette ne se distingue pas d'un don déguisé. L'emprunt se crée au dépôt du
    contrat, le reste — taux, durée — se complète dans l'onglet Emprunts.
    """
    prets = list(s.scalars(_valides(select(Recette), Recette)
                           .where(Recette.categorie == enums.CategorieRecette.pret)
                           .order_by(Recette.num_piece)).all())
    if not prets:
        return _section("contrats_pret", "Contrats de prêt", 0, 0, [],
                        note="Aucun prêt enregistré")
    emprunts = {e.id: e for e in s.scalars(select(Emprunt)).all()}
    sans_contrat = [r for r in prets
                    if not (r.emprunt_id and emprunts.get(r.emprunt_id)
                            and emprunts[r.emprunt_id].contrat_doc_id)]
    manquants = [_libelle_ecriture(r.num_piece,
                                   r.donateur.nom if r.donateur else "Prêt",
                                   r.montant, "prêt") for r in sans_contrat]
    actions = [{"type": "contrat_pret", "id": r.id, "num_piece": r.num_piece,
                "libelle": r.donateur.nom if r.donateur else "Prêt",
                "tiers": None, "montant": r.montant} for r in sans_contrat]
    total = len(prets)
    return _section(
        "contrats_pret", "Contrats de prêt", total, total - len(manquants),
        manquants, actions=actions,
        note=f"{total - len(manquants)}/{total} prêts sous contrat",
    )


def _section_evenements(s) -> dict:
    """Dépenses validées ni rattachées à un événement, ni déclarées hors événement.

    Presque toute dépense relève d'un moment de campagne — même la colle d'un
    collage. Le drapeau `hors_evenement` existe pour les rares exceptions : sans
    lui, on ne distinguerait pas « pas encore arbitré » de « rien à rattacher »,
    et la section ne tomberait jamais à zéro.
    """
    depenses = list(s.scalars(_valides(select(Depense), Depense)
                              .order_by(Depense.num_piece)).all())
    if not depenses:
        return _section("evenements", "Rattachement aux événements", 0, 0, [],
                        note="Aucune dépense enregistrée")
    rattachees = {l.depense_id for l in s.scalars(select(EvenementDepense)).all()}
    orphelines = [d for d in depenses
                  if d.id not in rattachees and not d.hors_evenement]
    manquants = [_libelle_ecriture(d.num_piece, d.nature, d.montant_ttc, "dépense")
                 for d in orphelines]
    actions = [{"type": "evenement", "id": d.id, "num_piece": d.num_piece,
                "libelle": d.nature or "dépense", "tiers": d.fournisseur,
                "montant": d.montant_ttc} for d in orphelines]
    total = len(depenses)
    return _section(
        "evenements", "Rattachement aux événements", total,
        total - len(manquants), manquants, actions=actions,
        note=f"{total - len(manquants)}/{total} dépenses situées",
    )


def _section_justificatifs_recettes(s) -> dict:
    """Recettes validées sans pièce au dossier (reçu, bordereau de remise…)."""
    recettes = list(s.scalars(_valides(select(Recette), Recette)
                              .order_by(Recette.num_piece)).all())
    sans_piece = [r for r in recettes if not r.justificatif_doc_id]
    manquants = [_libelle_ecriture(r.num_piece, _CATEGORIE_RECETTE.get(r.categorie),
                                   r.montant, "recette") for r in sans_piece]
    actions = [{"type": "recette", "id": r.id, "num_piece": r.num_piece,
                "libelle": _CATEGORIE_RECETTE.get(r.categorie) or "recette",
                "tiers": r.donateur.nom if r.donateur else None,
                "montant": r.montant} for r in sans_piece]
    total = len(recettes)
    return _section(
        "justificatifs_recettes", "Justificatifs de recettes", total,
        total - len(manquants), manquants, actions=actions,
        note=f"{total - len(manquants)}/{total} recettes justifiées" if total else
             "Aucune recette enregistrée",
    )


def _section_rapprochement(campaign_id: str, aucun_releve: bool = False) -> dict:
    """Écritures que le relevé bancaire ne justifie pas encore.

    Le compte de campagne doit se lire ligne à ligne sur le relevé : une
    dépense ou une recette qu'aucun mouvement bancaire ne porte est exactement
    ce que la commission cherche. Les concours en nature font exception — ils
    ne passent pas par le compte, c'est leur définition.
    """
    import releves
    total_ecritures = _nb_ecritures_rapprochables(campaign_id)
    if aucun_releve:
        # Énumérer les écritures n'apprendrait rien : il n'y a pas de relevé en
        # face. Un seul manque, une seule action.
        return _section(
            "rapprochement", "Rapprochement bancaire", total_ecritures, 0,
            [f"Aucun relevé importé — {total_ecritures} écriture"
             f"{'s' if total_ecritures > 1 else ''} à rapprocher"] if total_ecritures else [],
            actions=[_vers_ecran("releves", "Importer un relevé")] if total_ecritures else [],
            note="Aucune écriture à rapprocher" if not total_ecritures else None,
        )

    depenses = [d for d in releves.depenses_a_rapprocher(campaign_id)]
    recettes = releves.recettes_a_rapprocher(campaign_id)
    manquants = (
        [f"Dépense {d['num_piece'] or ''} — {d['libelle']} ({d['reste']:.0f} € non rapprochés)".replace("  ", " ")
         for d in depenses]
        + [f"Recette {r['num_piece'] or ''} — {r['libelle']} ({r['reste']:.0f} € non rapprochés)".replace("  ", " ")
           for r in recettes]
    )
    total = total_ecritures
    return _section(
        "rapprochement", "Rapprochement bancaire", total,
        max(total - len(manquants), 0), manquants,
        actions=[_vers_ecran("releves", "Rapprocher dans Relevés")] if manquants else [],
        note=f"{max(total - len(manquants), 0)}/{total} écritures rapprochées" if total else
             "Aucune écriture à rapprocher",
    )


def _nb_ecritures_rapprochables(campaign_id: str) -> int:
    """Dépenses (hors concours en nature) et recettes validées."""
    with campaign_session(campaign_id) as s:
        depenses = sum(1 for d in s.scalars(_valides(select(Depense), Depense)).all()
                       if d.statut != enums.StatutDepense.realise_nature)
        recettes = len(list(s.scalars(_valides(select(Recette), Recette)).all()))
    return depenses + recettes


def evaluer(campaign_id: str) -> dict:
    """État de complétude du dossier, section par section."""
    ensure_campaign_db(campaign_id)
    with campaign_session(campaign_id) as s:
        election = s.scalars(select(Election)).first()
        candidat = s.scalars(select(Candidat)).first()
        mandataire = s.scalars(select(Mandataire)).first()
        expert = s.scalars(select(ExpertComptable)).first()
        compte = s.scalars(select(CompteBancaire)).first()
        colistiers = list(s.scalars(select(Colistier)).all())

        vers_identite = lambda cle: [_vers_ecran("identite", "Compléter dans Identité", cle)]
        sections = [
            _section("election", "Élection", len(CHAMPS_ELECTION),
                     *_evaluer_objet(election, CHAMPS_ELECTION),
                     actions=vers_identite("election")),
            _section("candidat", "Candidat", len(CHAMPS_CANDIDAT),
                     *_evaluer_objet(candidat, CHAMPS_CANDIDAT),
                     actions=vers_identite("candidat")),
            _section("mandataire", "Mandataire financier", len(CHAMPS_MANDATAIRE),
                     *_evaluer_objet(mandataire, CHAMPS_MANDATAIRE),
                     actions=vers_identite("mandataire")),
        ]

        # L'expert-comptable est obligatoire sauf dispense explicite du compte.
        if expert is not None and expert.dispense:
            sections.append(_section("expert_comptable", "Expert-comptable", 1, 1, [],
                                     note="Compte dispensé d'expert-comptable"))
        else:
            sections.append(_section("expert_comptable", "Expert-comptable", len(CHAMPS_EXPERT),
                                     *_evaluer_objet(expert, CHAMPS_EXPERT),
                                     note=None if expert else "Aucun expert-comptable enregistré",
                                     actions=vers_identite("expert_comptable")))

        sections.append(_section("compte_bancaire", "Compte bancaire", len(CHAMPS_COMPTE),
                                 *_evaluer_objet(compte, CHAMPS_COMPTE),
                                 actions=vers_identite("compte_bancaire")))
        sections.append(_section_liste(colistiers))

        # Les justificatifs pèsent dans le score : ce sont eux qui restent à
        # réunir quand tout le reste est saisi, et leur absence empêche le dépôt.
        sections.append(_section_justificatifs_depenses(s))
        sections.append(_section_justificatifs_recettes(s))
        sections.append(_section_evenements(s))
        sections.append(_section_contrats_pret(s))

    # Récépissés de candidature et de déclaration du mandataire : exigés en
    # enveloppe B, et jusqu'ici ni demandés ni contrôlés par l'application.
    import identite
    pieces = identite.list_pieces_declaratives(campaign_id)
    # L'accord exprès du mandataire n'est pas systématiquement exigé : il ne
    # bloque pas le dépôt, contrairement aux deux récépissés.
    exigees = [p for p in pieces if p["cle"] != "accord-mandataire"]
    manquantes = [p["libelle"] for p in exigees if not p["fournie"]]
    sections.append(_section(
        "pieces_declaratives", "Pièces déclaratives", len(exigees),
        len(exigees) - len(manquantes), manquantes,
        actions=[{"type": "piece_declarative", "cle": p["cle"], "libelle": p["libelle"]}
                 for p in exigees if not p["fournie"]],
    ))

    # Le relevé bancaire est exigé en enveloppe B : lui seul atteste du
    # règlement effectif des dépenses. Sans lui, le dossier est incomplet quelle
    # que soit la qualité du reste.
    import releves
    liste_releves = releves.list_releves(campaign_id)
    nb_releves = len(liste_releves)
    if not nb_releves:
        sections.append(_section(
            "releves", "Relevés bancaires", 1, 0, ["Aucun relevé bancaire importé"],
            actions=[_vers_ecran("releves", "Importer ou saisir un relevé")],
        ))
    else:
        # Le relevé compte deux fois : comme source des transactions, et comme
        # pièce de l'enveloppe B. Des lignes saisies à la main sans le relevé
        # scanné laissent le dossier incomplet, ce que rien ne signalait.
        sans_piece = [r for r in liste_releves if not r.get("fichier")]
        sections.append(_section(
            "releves", "Relevés bancaires", nb_releves, nb_releves - len(sans_piece),
            [f"Relevé « {r['libelle']} » : le document d'origine manque"
             for r in sans_piece],
            actions=[{"type": "releve_piece", "id": r["id"], "libelle": r["libelle"],
                      "tiers": None, "montant": None, "num_piece": None}
                     for r in sans_piece],
            note=f"{nb_releves - len(sans_piece)}/{nb_releves} relevés au dossier",
        ))

    # Compte toujours, relevé importé ou non : sans ce décompte, un dossier
    # dont aucune écriture n'est rapprochée s'affichait à 95 %, alors qu'il est
    # très loin d'être déposable. Sans relevé, la section se résume à une ligne
    # plutôt que d'énumérer toutes les écritures — le manque est unique.
    sections.append(_section_rapprochement(campaign_id, aucun_releve=not nb_releves))

    # Pièces annoncées au bordereau mais absentes du disque : l'enveloppe
    # partirait avec un trou que rien ne signale au dépôt.
    import depot  # import tardif : depot dépend de conformite, pas l'inverse.
    absentes = depot.pieces_sans_fichier(campaign_id)
    sections.append(_section(
        "pieces", "Pièces justificatives", 1, 0 if absentes else 1,
        [f"Fichier introuvable : {f}" for f in absentes],
        note=None if absentes else "Tous les fichiers sont présents",
        actions=[_vers_ecran("depot", "Vérifier dans Dépôt")] if absentes else [],
    ))

    requis = sum(sec["requis"] for sec in sections)
    remplis = sum(sec["remplis"] for sec in sections)
    manquants = [f"{sec['titre']} — {m}" for sec in sections for m in sec["manquants"]]

    return {
        "sections": sections,
        "requis": requis,
        "remplis": remplis,
        "pct": round(remplis / requis * 100) if requis else 100,
        "complet": not manquants,
        "manquants": manquants,
    }
