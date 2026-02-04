
from fpdf import FPDF
import os
from datetime import datetime

class CertificatePDF(FPDF):
    def header(self):
        # Logo ou titre
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Élections Municipales 2026', border=0, ln=1, align='C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, 'Mandataire Financier de M. Mathieu Garabedian', border=0, ln=1, align='C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', align='C')

def generate_donation_receipt(data, signature_path):
    pdf = CertificatePDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)

    # Titre
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 20, "REÇU DE DON POUR CAMPAGNE ÉLECTORALE", ln=True, align='C')
    pdf.ln(10)

    # Corps
    pdf.set_font("helvetica", size=12)
    text = f"""
Je soussigné, Gaëtan CONSTANT MAGNARD, mandataire financier, certifie avoir reçu ce jour :
La somme de : {data['montant']} EUR
De la part de : {data['nom_donateur']}
Demeurant à : {data['adresse']}

Nature du versement : {data['type']}
Date du versement : {data['date']}

Ce reçu est délivré pour valoir ce que de droit dans le cadre de la législation sur le financement des campagnes électorales.
    """
    pdf.multi_cell(0, 10, text)
    
    pdf.ln(20)
    
    # Signature
    pdf.cell(0, 10, f"Fait à Villeurbanne, le {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='R')
    pdf.ln(5)
    
    if os.path.exists(signature_path):
        # Agrandissement supplémentaire de la signature
        pdf.image(signature_path, x=115, y=pdf.get_y(), w=80)

    return pdf.output()

def generate_expense_certification(data, signature_path):
    pdf = CertificatePDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)

    # Titre
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 20, "ATTESTATION D'ENGAGEMENT DE DÉPENSE", ln=True, align='C')
    pdf.ln(10)

    # Corps
    pdf.set_font("helvetica", size=12)
    text = f"""
En ma qualité de mandataire financier de la campagne électorale de M. Mathieu Garabedian, 
j'atteste par la présente l'engagement de la dépense suivante :

Libellé : {data['libelle']}
Fournisseur : {data['fournisseur']}
Montant TTC : {data['montant_ttc']} EUR
Catégorie CNCCFP : {data['categorie_cnccfp']}
Date : {data['date']}

La présente attestation vise à régulariser le compte de campagne conformément aux dispositions du Code Électoral.
    """
    pdf.multi_cell(0, 10, text)
    
    pdf.ln(20)
    
    # Signature
    pdf.cell(0, 10, f"Fait à Villeurbanne, le {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='R')
    pdf.ln(5)
    
    if os.path.exists(signature_path):
        # Agrandissement supplémentaire de la signature
        pdf.image(signature_path, x=115, y=pdf.get_y(), w=80)

    return pdf.output()
