"""Croise les grands électeurs sénatoriaux (XLSX) avec la liste électorale (CSV)
pour récupérer adresse + date de naissance.

Sortie : grands_electeurs_avec_coordonnees.csv
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import openpyxl

BASE = Path(__file__).parent
CSV_ROLL = BASE / "ListeElecteursActifs-dep69-02-07-2026-09h44.csv"
XLSX = BASE / "VD_Tableau des électeurs_sénatoriaux_69_au_12-06-2026.xlsx"
OUT = BASE / "grands_electeurs_avec_coordonnees.csv"

# Mots-clés séparant nom de naissance / nom d'usage dans le tableau sénatorial
_EPOUSE = re.compile(r"\b(EPOUSE|EP|NEE|NE|VVE|VEUVE|DIT|DITE)\b")


def norm(s: str | None) -> str:
    """Majuscule, sans accents, sans ponctuation ni suffixe '(2)'."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"\(\d+\)", " ", s)
    s = re.sub(r"[^A-Za-z ]", " ", s).upper()
    return re.sub(r"\s+", " ", s).strip()


def surname_variants(nom_raw: str) -> list[str]:
    """Découpe un nom composé nom de naissance / nom d'épouse en variantes."""
    n = norm(nom_raw)
    parts = [p.strip() for p in _EPOUSE.split(n) if p.strip() and not _EPOUSE.fullmatch(p.strip())]
    variants = {n}
    variants.update(parts)
    return [v for v in variants if v]


def prenom_tokens(p_raw: str | None) -> list[str]:
    return norm(p_raw).split()


# ---------------------------------------------------------------------------
# 1) Index de la liste électorale
# ---------------------------------------------------------------------------
# Par commune : liste de tuples (noms_possibles:set, prenoms:set, record)
# record = (nom_affiche, prenoms, dob, adresse, cp, commune)
by_commune: dict[str, list] = defaultdict(list)
# Index global (pour la feuille sans commune) : nom -> liste de records
by_nom: dict[str, list] = defaultdict(list)

print("Indexation de la liste électorale…")
with open(CSV_ROLL, encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=";")
    for i, row in enumerate(reader):
        nom_naiss = norm(row["nom de naissance"])
        nom_usage = norm(row["nom d'usage"])
        noms = {n for n in (nom_naiss, nom_usage) if n}
        # tokens de tous les noms (pour matcher un nom composé partiel)
        nom_tokens = set()
        for n in noms:
            nom_tokens.update(n.split())
        prenoms = set(row["prénoms"].split()) if row["prénoms"] else set()
        prenoms_norm = set(prenom_tokens(row["prénoms"]))

        adresse = " ".join(
            p.strip()
            for p in (
                row["numéro de voie"],
                row["libellé de voie"],
                row["complément 1"],
                row["complément 2"],
                row["lieu-dit"],
            )
            if p and p.strip()
        )
        record = {
            "nom": " ".join(sorted(noms)) if noms else "",
            "nom_affiche": row["nom d'usage"] or row["nom de naissance"],
            "prenoms": row["prénoms"],
            "dob": row["date de naissance"],
            "adresse": adresse,
            "cp": row["code postal"],
            "commune": row["commune"],
        }
        entry = (noms, nom_tokens, prenoms_norm, record)
        by_commune[norm(row["commune"])].append(entry)
        for n in noms:
            by_nom[n].append(entry)
print(f"  {i + 1:,} électeurs indexés, {len(by_commune)} communes.")


def match_candidate(entry, xlsx_surnames: list[str], xlsx_prenom: list[str]) -> int:
    """Score : 2 = nom+prénom exact ; 1 = nom ok, prénom incertain ; 0 = non."""
    noms, nom_tokens, prenoms_norm, _ = entry
    # -- nom --
    surname_ok = False
    for v in xlsx_surnames:
        if v in noms:
            surname_ok = True
            break
        vt = set(v.split())
        if vt and vt.issubset(nom_tokens):  # nom composé : tokens présents
            surname_ok = True
            break
    if not surname_ok:
        return 0
    # -- prénom --
    if not xlsx_prenom:
        return 1
    if xlsx_prenom[0] in prenoms_norm:
        return 2
    # tolère un 2e prénom d'usage
    if any(p in prenoms_norm for p in xlsx_prenom):
        return 2
    return 1


def find(commune_raw: str | None, nom_raw: str, prenom_raw: str):
    """Retourne (statut, record|None). statut ∈ ok/ambigu/non_trouvé."""
    surnames = surname_variants(nom_raw)
    prenom = prenom_tokens(prenom_raw)

    pool = by_commune.get(norm(commune_raw)) if commune_raw else None
    global_search = pool is None
    if pool is None:
        # feuille sans commune : recherche globale sur le nom
        pool = []
        seen = set()
        for v in surnames:
            for e in by_nom.get(v, ()):
                if id(e) not in seen:
                    seen.add(id(e))
                    pool.append(e)

    best2, best1 = [], []
    for e in pool:
        sc = match_candidate(e, surnames, prenom)
        if sc == 2:
            best2.append(e)
        elif sc == 1:
            best1.append(e)

    hits = best2 or best1
    if len(hits) == 1:
        return "ok", hits[0][3]
    if len(hits) > 1:
        # départage par prénom exact complet si possible
        exact = [e for e in hits if prenom and prenom == list(prenom_tokens(e[3]["prenoms"]))[: len(prenom)]]
        if len(exact) == 1:
            return "ok", exact[0][3]
        return "ambigu", hits[0][3]  # on renvoie le 1er + flag
    return "non_trouvé", None


# ---------------------------------------------------------------------------
# 2) Parcours des grands électeurs
# ---------------------------------------------------------------------------
print("Lecture du tableau sénatorial…")
wb = openpyxl.load_workbook(XLSX, read_only=True)

out_rows = []
stats = defaultdict(int)

# Feuille COMMUNES : commune | catégorie | nom | prénom
ws = wb["COMMUNES"]
for row in list(ws.iter_rows(values_only=True))[2:]:
    commune, cat, nom, prenom = row[0], row[1], row[2], row[3]
    if not nom:
        continue
    statut, rec = find(commune, nom, prenom)
    stats[statut] += 1
    out_rows.append(
        {
            "source": "COMMUNE",
            "commune_mandat": commune,
            "mandat_categorie": cat,
            "nom_tableau": nom,
            "prenom_tableau": prenom,
            "statut_match": statut,
            "nom_liste": rec["nom_affiche"] if rec else "",
            "prenoms_liste": rec["prenoms"] if rec else "",
            "date_naissance": rec["dob"] if rec else "",
            "adresse": rec["adresse"] if rec else "",
            "code_postal": rec["cp"] if rec else "",
            "commune_liste": rec["commune"] if rec else "",
        }
    )

# Feuille conseillers départementaux / métropole : mandat | nom | prénom | remplacement
ws = wb["DÉP SEN CD CMETRO"]
for row in list(ws.iter_rows(values_only=True))[1:]:
    mandat, nom, prenom = row[0], row[1], row[2]
    if not nom:
        continue
    statut, rec = find(None, nom, prenom)
    stats[statut] += 1
    out_rows.append(
        {
            "source": "DEP_METRO",
            "commune_mandat": "",
            "mandat_categorie": mandat,
            "nom_tableau": nom,
            "prenom_tableau": prenom,
            "statut_match": statut,
            "nom_liste": rec["nom_affiche"] if rec else "",
            "prenoms_liste": rec["prenoms"] if rec else "",
            "date_naissance": rec["dob"] if rec else "",
            "adresse": rec["adresse"] if rec else "",
            "code_postal": rec["cp"] if rec else "",
            "commune_liste": rec["commune"] if rec else "",
        }
    )

# ---------------------------------------------------------------------------
# 3) Écriture
# ---------------------------------------------------------------------------
fields = [
    "source",
    "commune_mandat",
    "mandat_categorie",
    "nom_tableau",
    "prenom_tableau",
    "statut_match",
    "nom_liste",
    "prenoms_liste",
    "date_naissance",
    "adresse",
    "code_postal",
    "commune_liste",
]
with open(OUT, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields, delimiter=";")
    w.writeheader()
    w.writerows(out_rows)

total = len(out_rows)
print(f"\n=== Résultat ({total} grands électeurs) ===")
for k in ("ok", "ambigu", "non_trouvé"):
    print(f"  {k:12s}: {stats[k]:5d} ({100 * stats[k] / total:.1f}%)")
print(f"\nFichier écrit : {OUT}")
