"""Pièces rattachées à un événement : classement en enveloppe et détachement."""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import evenements
from db.session import campaign_session
from db.models import Depense, Document
from db import enums
from _fixture import fresh_campaign, teardown, run_tests


def _evenement(cid: str) -> int:
    return evenements.create_evenement(cid, evenements.EvenementIn(
        titre="Réunion publique", type="reunion_publique", date_debut="2026-09-10",
        lieu="Villeurbanne"))["id"]


def test_photo_classee_en_annexe_facture_en_piece_de_depense():
    """Le classement vient du type : une photo est une annexe (B), pas une pièce de A."""
    cid = fresh_campaign()
    try:
        eid = _evenement(cid)
        evenements.link_document(cid, eid, evenements.DocumentEvenementIn(
            fichier="/data/uploads/meeting.jpg", type="photo"))
        evenements.link_document(cid, eid, evenements.DocumentEvenementIn(
            fichier="/data/uploads/salle.pdf", type="facture"))

        par_type = {d["type"]: d for d in evenements.list_documents_evenement(cid, eid)}
        assert par_type["photo"]["enveloppe"] == "B"
        assert par_type["facture"]["enveloppe"] == "A"
    finally:
        teardown(cid)


def test_detacher_une_piece_ne_la_supprime_pas():
    """La facture d'une dépense reste au dossier même détachée de l'événement."""
    cid = fresh_campaign()
    try:
        eid = _evenement(cid)
        with campaign_session(cid) as s:
            doc = Document(type=enums.TypeDocument.facture, media_type="pdf",
                           fichier="facture.pdf", enveloppe=enums.Enveloppe.A)
            s.add(doc)
            s.flush()
            doc_id = doc.id

        evenements.link_document(cid, eid, evenements.DocumentEvenementIn(doc_id=doc_id, type="facture"))
        assert len(evenements.list_documents_evenement(cid, eid)) == 1

        evenements.unlink_document(cid, eid, doc_id)
        assert evenements.list_documents_evenement(cid, eid) == []
        with campaign_session(cid) as s:
            assert s.get(Document, doc_id) is not None, "la pièce doit rester au dossier"
    finally:
        teardown(cid)


def test_rattacher_une_piece_existante_conserve_son_enveloppe():
    """Une facture déjà classée en A ne doit pas basculer en B en devenant preuve d'événement."""
    cid = fresh_campaign()
    try:
        eid = _evenement(cid)
        with campaign_session(cid) as s:
            doc = Document(type=enums.TypeDocument.facture, media_type="pdf",
                           fichier="deja_classee.pdf", enveloppe=enums.Enveloppe.A)
            s.add(doc)
            s.flush()
            doc_id = doc.id

        evenements.link_document(cid, eid, evenements.DocumentEvenementIn(doc_id=doc_id, type="photo"))
        piece = evenements.list_documents_evenement(cid, eid)[0]
        assert piece["enveloppe"] == "A"
    finally:
        teardown(cid)


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
