"""
Générateur de conventions.
Produit un PDF via WeasyPrint (HTML → PDF).

Types disponibles :
  - ConventionMutualisation : répartition de dépenses entre candidats
  - ConventionLocal        : mise à disposition du local « Local Pop' »
"""

import logging
import os
from datetime import date

# WeasyPrint nécessite Pango/GLib installés via Homebrew sur macOS
os.environ.setdefault("DYLD_LIBRARY_PATH", "/opt/homebrew/lib")

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Template
from weasyprint import HTML

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

CONVENTIONS_DIR = Path(__file__).parent
OUTPUT_DIR = CONVENTIONS_DIR / "output"

PERIODE_DEBUT = date(2025, 9, 1)
PERIODE_FIN = date(2026, 3, 30)
NB_JOURS_LOCAL = (PERIODE_FIN - PERIODE_DEBUT).days + 1  # 211 jours


# ──────────────────────────────────────────────
# Convention de mutualisation de dépenses
# ──────────────────────────────────────────────

@dataclass
class ConventionMutualisation:
    conv_num: str
    nature_depense: str
    description_depense: list[str]   # liste de lignes affichées sous tirets
    nb_factures: int
    part_garabedian: str
    part_amard: str
    date_signature: str
    montant_garabedian: str = ""         # optionnel, ex: "542,70"
    montant_amard: str = ""              # optionnel, ex: "180,90"
    justification: list[str] = field(default_factory=list)  # optionnel
    filename: str = ""


def generate_mutualisation(data: ConventionMutualisation) -> Path:
    slug = data.filename or data.conv_num.replace("/", "-")
    return _render(
        template_path=CONVENTIONS_DIR / "template.html",
        context=data.__dict__,
        filename=slug,
    )


# ──────────────────────────────────────────────
# Convention de mise à disposition du local
# ──────────────────────────────────────────────

@dataclass
class ConventionLocal:
    conv_num: str
    montant: str
    date_signature: str
    nb_jours: int = field(default=NB_JOURS_LOCAL)
    filename: str = ""


def generate_local(data: ConventionLocal) -> Path:
    slug = data.filename or data.conv_num.replace("/", "-")
    return _render(
        template_path=CONVENTIONS_DIR / "template_local.html",
        context=data.__dict__,
        filename=slug,
    )


# ──────────────────────────────────────────────
# Moteur de rendu commun
# ──────────────────────────────────────────────

def _render(template_path: Path, context: dict, filename: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"{filename}.pdf"
    html_content = Template(template_path.read_text(encoding="utf-8")).render(**context)
    HTML(string=html_content, base_url=str(CONVENTIONS_DIR)).write_pdf(str(output_path))
    log.info("PDF généré → %s", output_path)
    return output_path


# ──────────────────────────────────────────────
# Exemples
# ──────────────────────────────────────────────

if __name__ == "__main__":
    generate_local(ConventionLocal(
        conv_num="CONV-LOCAL-001",
        montant="9 800,00",
        date_signature="__ ________ 2026",
        filename="CONV-LOCAL-001_mise-a-disposition-local-pop",
    ))

    generate_mutualisation(ConventionMutualisation(
        conv_num="CONV-006",
        nature_depense="Utilisation du local « Local Pop' » pour le stockage du matériel de campagne",
        description_depense=[
            "Coût de mise à disposition du local « Local Pop' », 18 avenue Blanqui, 69100 Villeurbanne — 9 800,00 € TTC (cf. CONV-LOCAL-001)",
        ],
        nb_factures=1,
        part_garabedian="93 %",
        part_amard="7 %",
        montant_garabedian="9 114,00",
        montant_amard="686,00",
        justification=[
            "Sur l'ensemble de la campagne, 70 000 tracts et affiches ont été utilisés au total.",
            "Parmi eux, 5 000 relèvent de la campagne métropolitaine de Gabriel Amard, soit 5 000 ÷ 70 000 × 100 = 7 %.",
            "Les 65 000 autres relèvent de la campagne municipale de Mathieu Garabedian, soit 65 000 ÷ 70 000 × 100 = 93 %.",
            "Cette clé de répartition s'applique au coût total de mise à disposition du local utilisé pour le stockage du matériel.",
        ],
        date_signature="__ ________ 2026",
        filename="CONV-006_stockage-materiel-local",
    ))

    generate_mutualisation(ConventionMutualisation(
        conv_num="CONV-002",
        nature_depense="Tracts porte-à-porte de soutien à Mathieu Garabedian et Gabriel Amard",
        description_depense=[
            "FACTURE N°202512.0312 — PublicImprim, 5 000 exemplaires, 693,60 € TTC",
        ],
        nb_factures=1,
        part_garabedian="75 %",
        part_amard="25 %",
        montant_garabedian="520,20",
        montant_amard="173,40",
        justification=[
            "Le tract contient 8 éléments politiques identifiables au total (6 propositions programmatiques + 2 photos principales en page 1).",
            "Parmi eux, 2 relèvent de la Métropole : 1 mesure métropolitaine (la gratuité des transports en commun) et 1 photo de Gabriel Amard, candidat métropolitain. Soit : 2 ÷ 8 × 100 = 25 %.",
            "Les 6 autres relèvent du municipal : 5 mesures municipales et 1 photo de Mathieu Garabedian, candidat municipal. Soit : 6 ÷ 8 × 100 = 75 %.",
        ],
        date_signature="__ ________ 2026",
        filename="CONV-002_tracts-porte-a-porte",
    ))

    generate_mutualisation(ConventionMutualisation(
        conv_num="CONV-003",
        nature_depense="Programme municipal et métropolitain",
        description_depense=[
            "FACTURE N°DC26010284 — PubAdresse, publipostage des programmes, 80 000 exemplaires, 31 721,80 € TTC",
            "FACTURE N°202601.395 — Imprimerie GRENIER, impression des programmes, 80 000 exemplaires, 23 784,00 € TTC (avoir de 825,77 € au 07/05/2026 → net : 22 958,23 € TTC)",
            "FACTURE N°20260123-00069 — VARSO, conception du programme, 3 669,00 € TTC",
            "Total : 58 349,03 € TTC",
        ],
        nb_factures=3,
        part_garabedian="83 %",
        part_amard="17 %",
        montant_garabedian="48 429,69",
        montant_amard="9 919,34",
        justification=[
            "Le programme compte 90 mesures au total.",
            "Parmi elles, 15 sont des mesures métropolitaines explicites, soit 15 ÷ 90 × 100 = 16,7 %.",
            "Les 75 autres mesures relèvent du champ municipal, soit 75 ÷ 90 × 100 = 83,3 %.",
            "Le programme est donc composé de 17 % de mesures métropolitaines et de 83 % de mesures municipales.",
        ],
        date_signature="__ ________ 2026",
        filename="CONV-003_programme-municipal-metropolitain",
    ))

    generate_mutualisation(ConventionMutualisation(
        conv_num="CONV-005",
        nature_depense="Barnum de campagne",
        description_depense=[
            "FACTURE N°OD126 705 — VITABRI, 1 barnum, 2 874,00 € TTC",
        ],
        nb_factures=1,
        part_garabedian="66,66 %",
        part_amard="33,33 %",
        montant_garabedian="1 915,81",
        montant_amard="957,99",
        justification=[
            "Le barnum comporte 3 faces. 1 face sur 3 est consacrée à la candidature de Gabriel Amard pour l'élection métropolitaine, soit 1 ÷ 3 × 100 = 33,33 %.",
            "Les 2 faces restantes relèvent de la campagne municipale de Mathieu Garabedian, soit 2 ÷ 3 × 100 = 66,66 %.",
        ],
        date_signature="__ ________ 2026",
        filename="CONV-005_barnum-campagne",
    ))

    # Bandeaux 1 à 4 — une seule facture PublicImprim couvre les 4 supports
    # Coût unitaire : 723,60 € / 4 = 180,90 € par bandeau
    # Bandeau 1 : 100 % municipal    → 180,90 €
    # Bandeau 2 : 100 % municipal    → 180,90 €
    # Bandeau 3 : 50 % / 50 %       → 90,45 € chacun
    # Bandeau 4 : 50 % / 50 %       → 90,45 € chacun
    # Total Garabedian : 542,70 € (3/4) — Total Amard : 180,90 € (1/4)
    generate_mutualisation(ConventionMutualisation(
        conv_num="CONV-004",
        nature_depense="Impression de bandeaux programmatiques (4 bandeaux)",
        description_depense=[
            "FACTURE N°202602.0114 — PublicImprim, 100 exemplaires, 723,60 € TTC",
            "Bandeau programmatique 1 — 100 % municipal (180,90 €)",
            "Bandeau programmatique 2 — 100 % municipal (180,90 €)",
            "Bandeau programmatique 3 — 50 % municipal / 50 % métropolitain (90,45 € / 90,45 €)",
            "Bandeau programmatique 4 — 50 % municipal / 50 % métropolitain (90,45 € / 90,45 €)",
        ],
        nb_factures=1,
        part_garabedian="3/4",
        part_amard="1/4",
        montant_garabedian="542,70",
        montant_amard="180,90",
        date_signature="__ ________ 2026",
        filename="CONV-004_bandeaux-programmatiques",
    ))
