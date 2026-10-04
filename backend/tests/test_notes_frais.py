"""Notes de frais : regrouper les avances d'une personne en un document."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

import comptes
import notes_frais
import releves
from models import Depense
from _fixture import fresh_campaign, teardown, run_tests


def _avance(cid, libelle, montant, qui="DUPONT Marc", fournisseur="Station Total"):
    comptes.create_depense(cid, Depense(
        date=date(2026, 9, 20), libelle=libelle, fournisseur=fournisseur,
        montant_ttc=montant, tva=0.0, categorie_cnccfp="D1", statut="Facturé",
        avance_par=qui))
    # Repérée par son libellé : plusieurs dépenses partagent la même date, et
    # la liste est triée par date — « la dernière » n'est pas fiable.
    return next(d["id"] for d in comptes.list_depenses(cid) if d["libelle"] == libelle)


def test_la_note_regroupe_les_avances_d_une_personne():
    cid = fresh_campaign()
    try:
        _avance(cid, "Essence", 38.40)
        _avance(cid, "Colle", 18.50, fournisseur="Papeterie")
        _avance(cid, "Péage", 12.00, qui="MARTIN Léa", fournisseur="APRR")

        note = notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="DUPONT Marc"))
        assert note["total"] == 56.90 and note["nb_lignes"] == 2, note
        assert note["remboursee"] is False, note
        # L'avance de Léa n'y est pas.
        assert all("Péage" != l["libelle"] for l in note["lignes"]), note["lignes"]
    finally:
        teardown(cid)


def test_une_depense_n_entre_que_dans_une_note():
    cid = fresh_campaign()
    try:
        _avance(cid, "Essence", 38.40)
        notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="DUPONT Marc"))
        raised = False
        try:
            notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="DUPONT Marc"))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400
        assert raised, "la seconde note n'avait plus rien à regrouper"
    finally:
        teardown(cid)


def test_la_note_est_remboursee_quand_le_compte_a_regle():
    """L'état se déduit du rapprochement : pas de case à cocher à tenir."""
    cid = fresh_campaign()
    try:
        a = _avance(cid, "Essence", 40.0)
        b = _avance(cid, "Colle", 20.0, fournisseur="Papeterie")
        note = notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="DUPONT Marc"))
        assert note["remboursee"] is False

        # Un seul virement de 60 € solde les deux lignes.
        r = releves.create_releve(cid, releves.ReleveIn(
            libelle="Septembre", source="manuel",
            transactions=[releves.TransactionIn(
                date_operation="2026-09-28", libelle="VIR DUPONT MARC",
                montant=60.0, sens="debit")]), "gaetan")
        tid = r["transactions"][0]["id"]
        for did in (a, b):
            releves.imputer(cid, tid, releves.ImputationIn(depense_id=did))

        assert notes_frais.list_notes(cid)[0]["remboursee"] is True
    finally:
        teardown(cid)


def test_un_remboursement_partiel_ne_solde_pas_la_note():
    cid = fresh_campaign()
    try:
        a = _avance(cid, "Essence", 40.0)
        _avance(cid, "Colle", 20.0, fournisseur="Papeterie")
        notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="DUPONT Marc"))
        r = releves.create_releve(cid, releves.ReleveIn(
            libelle="Septembre", source="manuel",
            transactions=[releves.TransactionIn(
                date_operation="2026-09-28", libelle="VIR DUPONT", montant=40.0,
                sens="debit", depense_id=a)]), "gaetan")
        assert r["transactions"][0]["rapprochee"] is True
        assert notes_frais.list_notes(cid)[0]["remboursee"] is False
    finally:
        teardown(cid)


def test_une_avance_deja_remboursee_n_entre_pas_dans_la_note():
    cid = fresh_campaign()
    try:
        a = _avance(cid, "Essence", 40.0)
        _avance(cid, "Colle", 20.0, fournisseur="Papeterie")
        releves.create_releve(cid, releves.ReleveIn(
            libelle="Septembre", source="manuel",
            transactions=[releves.TransactionIn(
                date_operation="2026-09-25", libelle="VIR", montant=40.0,
                sens="debit", depense_id=a)]), "gaetan")
        note = notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="DUPONT Marc"))
        assert note["nb_lignes"] == 1 and note["total"] == 20.0, note
    finally:
        teardown(cid)


def test_supprimer_la_note_conserve_les_depenses():
    """Les dépenses existent indépendamment du document qui les regroupe."""
    cid = fresh_campaign()
    try:
        _avance(cid, "Essence", 38.40)
        note = notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="DUPONT Marc"))
        notes_frais.delete_note(cid, note["id"])
        assert notes_frais.list_notes(cid) == []
        assert len(comptes.list_depenses(cid)) == 1
        # L'avance redevient regroupable.
        assert comptes.avances_a_rembourser(cid)[0]["total"] == 38.40
    finally:
        teardown(cid)


def test_sans_avance_la_note_est_refusee():
    cid = fresh_campaign()
    try:
        raised = False
        try:
            notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="INCONNU"))
        except HTTPException as e:
            raised = True
            assert e.status_code == 400 and "INCONNU" in e.detail
        assert raised
    finally:
        teardown(cid)


def test_le_pdf_porte_le_total_et_la_signature():
    cid = fresh_campaign()
    try:
        _avance(cid, "Essence", 38.40)
        _avance(cid, "Colle", 18.50, fournisseur="Papeterie")
        note = notes_frais.create_note(cid, notes_frais.NoteFraisIn(personne="DUPONT Marc"))
        pdf = notes_frais.export_pdf(cid, note["id"])
        assert pdf.startswith(b"%PDF") and len(pdf) > 1000, len(pdf)
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
