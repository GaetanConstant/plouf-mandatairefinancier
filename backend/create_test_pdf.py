from reportlab.pdfgen import canvas
import random
from datetime import datetime

def create_receipt_pdf(filename: str):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "FACTURE n°2026-0001")
    c.drawString(100, 730, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
    c.drawString(100, 710, "Fournisseur: Imprimerie Villeurbanne")
    
    amount = 123.45
    c.drawString(100, 680, "Produit: Impression flyer")
    c.drawString(300, 680, "100.00 €")
    c.drawString(100, 660, "TVA 20%")
    c.drawString(300, 660, "23.45 €")
    
    c.drawString(100, 630, "Montant TTC:")
    c.drawString(300, 630, f"{amount} €")
    c.save()

if __name__ == "__main__":
    create_receipt_pdf("test_receipt.pdf")
    print("test_receipt.pdf created.")
