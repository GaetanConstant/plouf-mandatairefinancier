"""Génère le CSV de décompte des sommes municipales / métropolitaines."""

import csv
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"

CONVENTIONS = [
    {
        "num": "CONV-006",
        "objet": "Stockage du matériel de campagne — local « Local Pop' »",
        "pct_municipal": 93,
        "pct_metro": 7,
        "factures": [
            {"num": "cf. CONV-LOCAL-001", "prestataire": "Local Pop'", "montant": 9800.00},
        ],
    },
    {
        "num": "CONV-002",
        "objet": "Tracts porte-à-porte Garabedian + Amard",
        "pct_municipal": 75,
        "pct_metro": 25,
        "factures": [
            {"num": "202512.0312", "prestataire": "PublicImprim", "montant": 693.60},
            {"num": "202603.0037", "prestataire": "PublicImprim", "montant": 508.51},
        ],
    },
    {
        "num": "CONV-003",
        "objet": "Programme municipal et métropolitain",
        "pct_municipal": 83,
        "pct_metro": 17,
        "factures": [
            {"num": "DC26010284",     "prestataire": "PubAdresse",        "montant": 31721.80},
            {"num": "202601.395",     "prestataire": "Imprimerie GRENIER","montant": 23784.00},
            {"num": "20260123-00069", "prestataire": "VARSO",             "montant":  3669.00},
        ],
    },
    {
        "num": "CONV-004",
        "objet": "Bandeaux programmatiques (4 bandeaux)",
        "pct_municipal": 75,
        "pct_metro": 25,
        "factures": [
            {"num": "202602.0114", "prestataire": "PublicImprim", "montant": 723.60},
        ],
    },
    {
        "num": "CONV-005",
        "objet": "Barnum de campagne",
        "pct_municipal": 67,
        "pct_metro": 33,
        "factures": [
            {"num": "OD126 705", "prestataire": "VITABRI", "montant": 2874.00},
        ],
    },
]

FIELDNAMES = [
    "N° Convention",
    "Objet",
    "N° Facture",
    "Prestataire",
    "Montant Facture TTC (€)",
    "% Municipal",
    "% Métropolitain",
    "Montant Garabedian (€)",
    "Montant Amard (€)",
]


def fmt(val: float) -> str:
    return f"{val:,.2f}".replace(",", " ").replace(".", ",")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / "decompte_mutualisation.csv"

    grand_total = grand_garabedian = grand_amard = 0.0

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
        writer.writeheader()

        for conv in CONVENTIONS:
            pct_muni = conv["pct_municipal"] / 100
            pct_metro = conv["pct_metro"] / 100
            total_conv = sum(fac["montant"] for fac in conv["factures"])

            for i, fac in enumerate(conv["factures"]):
                garabedian = round(fac["montant"] * pct_muni, 2)
                amard = round(fac["montant"] * pct_metro, 2)
                writer.writerow({
                    "N° Convention": conv["num"] if i == 0 else "",
                    "Objet": conv["objet"] if i == 0 else "",
                    "N° Facture": fac["num"],
                    "Prestataire": fac["prestataire"],
                    "Montant Facture TTC (€)": fmt(fac["montant"]),
                    "% Municipal": f"{conv['pct_municipal']} %" if i == 0 else "",
                    "% Métropolitain": f"{conv['pct_metro']} %" if i == 0 else "",
                    "Montant Garabedian (€)": fmt(garabedian),
                    "Montant Amard (€)": fmt(amard),
                })

            # Sous-total convention si plusieurs factures
            if len(conv["factures"]) > 1:
                sub_garabedian = round(total_conv * pct_muni, 2)
                sub_amard = round(total_conv * pct_metro, 2)
                writer.writerow({
                    "N° Convention": "",
                    "Objet": f"Sous-total {conv['num']}",
                    "N° Facture": "",
                    "Prestataire": "",
                    "Montant Facture TTC (€)": fmt(total_conv),
                    "% Municipal": "",
                    "% Métropolitain": "",
                    "Montant Garabedian (€)": fmt(sub_garabedian),
                    "Montant Amard (€)": fmt(sub_amard),
                })

            grand_total += total_conv
            grand_garabedian += round(total_conv * pct_muni, 2)
            grand_amard += round(total_conv * pct_metro, 2)

        # Ligne vide + total général
        writer.writerow({f: "" for f in FIELDNAMES})
        writer.writerow({
            "N° Convention": "TOTAL",
            "Objet": "",
            "N° Facture": "",
            "Prestataire": "",
            "Montant Facture TTC (€)": fmt(grand_total),
            "% Municipal": "",
            "% Métropolitain": "",
            "Montant Garabedian (€)": fmt(grand_garabedian),
            "Montant Amard (€)": fmt(grand_amard),
        })

    print(f"CSV généré → {output_path}")
    print(f"\nTotal TTC        : {fmt(grand_total)} €")
    print(f"Garabedian (muni) : {fmt(grand_garabedian)} €")
    print(f"Amard (métro)     : {fmt(grand_amard)} €")


if __name__ == "__main__":
    main()
