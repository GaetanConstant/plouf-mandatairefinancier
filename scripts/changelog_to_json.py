"""Génère le JSON de l'onglet « À propos » à partir de CHANGELOG.md.

CHANGELOG.md est la source de vérité de l'historique des versions. Le frontend
ne sait pas lire du markdown : ce script le convertit en JSON structuré, importé
directement par la page À propos.

À relancer après chaque entrée ajoutée au changelog :

    uv run scripts/changelog_to_json.py
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ## v2.10.0 — 2026-09-09 — Onglet Prévisionnel
#             ^ date ISO, jour optionnel   ^ titre
EN_TETE = re.compile(
    r"^##\s+v(?P<version>\d+\.\d+\.\d+)\s+[—-]\s+"
    r"(?P<date>\d{4}-\d{2}(?:-\d{2})?)\s+[—-]\s+"
    r"(?P<titre>.+?)\s*$"
)
PUCE = re.compile(r"^[-*]\s+(?P<texte>.+?)\s*$")

MOIS = (
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def date_en_francais(iso: str) -> str:
    """Rend une date ISO en français, en respectant sa précision.

    Le changelog accepte `YYYY-MM-DD` comme `YYYY-MM` : les premières versions
    ne sont datées qu'au mois. On ne fabrique pas un jour qui n'existe pas.
    """
    morceaux = iso.split("-")
    annee, mois = int(morceaux[0]), int(morceaux[1])
    if len(morceaux) == 2:
        return f"{MOIS[mois - 1]} {annee}"
    return f"{int(morceaux[2])} {MOIS[mois - 1]} {annee}"


def parser_changelog(contenu: str) -> list[dict[str, object]]:
    """Extrait les versions du changelog, dans l'ordre du fichier."""
    versions: list[dict[str, object]] = []
    courante: dict[str, object] | None = None

    for ligne in contenu.splitlines():
        entete = EN_TETE.match(ligne)
        if entete is not None:
            version = entete["version"]
            courante = {
                "version": f"v{version}",
                "date": entete["date"],
                "dateAffichee": date_en_francais(entete["date"]),
                "titre": entete["titre"],
                "details": [],
                # Un palier majeur est une version vX.0.0 : elle est mise en
                # évidence dans la page. Pas de marqueur à maintenir à la main.
                "majeur": bool(re.fullmatch(r"\d+\.0\.0", version)),
            }
            versions.append(courante)
            continue

        if courante is None:
            # Préambule du fichier, avant la première version.
            continue

        puce = PUCE.match(ligne)
        if puce is not None:
            details = courante["details"]
            assert isinstance(details, list)
            details.append(puce["texte"])

    # La toute première version est la création de l'application : c'est un
    # palier, même si son numéro n'est pas un vX.0.0.
    if versions:
        versions[-1]["majeur"] = True

    return versions


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--changelog", type=Path, default=Path("CHANGELOG.md"),
        help="chemin du changelog source (défaut : CHANGELOG.md)",
    )
    parser.add_argument(
        "--sortie", type=Path, default=Path("frontend/src/data/versions.json"),
        help="chemin du JSON généré",
    )
    parser.add_argument(
        "--version-file", type=Path, default=Path("VERSION"),
        help="fichier du numéro courant, vérifié contre le changelog",
    )
    args = parser.parse_args()

    if not args.changelog.is_file():
        logger.error("changelog introuvable : %s", args.changelog)
        return 1

    versions = parser_changelog(args.changelog.read_text(encoding="utf-8"))
    if not versions:
        logger.error("aucune version reconnue dans %s — format d'en-tête incorrect ?", args.changelog)
        return 1

    # VERSION et CHANGELOG.md doivent désigner le même numéro : sinon l'onglet
    # « À propos » afficherait une version que le dépôt ne revendique pas.
    courante = str(versions[0]["version"]).lstrip("v")
    if args.version_file.is_file():
        declaree = args.version_file.read_text(encoding="utf-8").strip().lstrip("v")
        if declaree != courante:
            logger.error(
                "%s déclare %s mais la dernière entrée du changelog est v%s — "
                "corriger l'un des deux avant de commiter",
                args.version_file, declaree, courante,
            )
            return 1
    else:
        logger.warning("%s absent : aucune vérification de cohérence", args.version_file)

    args.sortie.parent.mkdir(parents=True, exist_ok=True)
    args.sortie.write_text(
        json.dumps(versions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    logger.info("%d versions écrites dans %s", len(versions), args.sortie)
    logger.info("version courante : %s", versions[0]["version"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
