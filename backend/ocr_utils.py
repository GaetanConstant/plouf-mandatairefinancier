
import io
import os
import re
import tempfile
import logging
from datetime import datetime
import pytesseract
from pdf2image import convert_from_path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """
    Extract text from PDF or Image using Tesseract OCR.
    """
    suffix = os.path.splitext(filename)[1].lower()
    if not suffix:
        suffix = ".tmp"
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    text_content = ""
    try:
        logger.info(f"Processing file with Tesseract: {tmp_path}")
        
        if suffix == ".pdf":
            # Convert PDF to images
            try:
                images = convert_from_path(tmp_path)
                texts = []
                for i, image in enumerate(images):
                    logger.info(f"Processing page {i+1}...")
                    # lang='fra' for French
                    page_text = pytesseract.image_to_string(image, lang='fra')
                    texts.append(page_text)
                text_content = "\n".join(texts)
            except Exception as e:
                logger.error(f"PDF conversion failed: {e}")
                text_content = ""
        else:
            # Assume image (jpg, png, etc.)
            try:
                # Need to use PIL Image or just path if tesseract supports it (it usually wants an Image object or path)
                import PIL.Image
                img = PIL.Image.open(tmp_path)
                text_content = pytesseract.image_to_string(img, lang='fra')
            except Exception as e:
                logger.error(f"Image processing failed: {e}")
                text_content = ""
            
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        text_content = f"Error during OCR: {str(e)}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
    return text_content

def analyze_receipt_text(text: str) -> dict:
    """
    Heuristic analysis of receipt text to find Amount, Date, Supplier.
    Uses extracted text from OCR.
    """
    print("--- EXTRACTED TEXT FROM TESSERACT START ---")
    print(text)
    print("--- EXTRACTED TEXT FROM TESSERACT END ---")

    result = {
        "montant": None,
        "date": None,
        "fournisseur": "Inconnu",
        "libelle": "Dépense détectée"
    }
    
    if not text:
        return result

    # 1. Find Amount
    # Tesseract might return 'E' for '€' or similar artifacts.
    # Regex allow spaces and common OCR errors for euro symbol
    amount_re = re.compile(r'(\d+[\.,]\d{2})\s*(?:€|EUR|euros?|E)', re.IGNORECASE)
    amounts = amount_re.findall(text)
    
    if not amounts:
        # Look for "Total 12.34"
        total_re = re.compile(r'(?:total|montant|net à payer)\s*[:\.]?\s*(\d+[\.,]\d{2})', re.IGNORECASE)
        amounts = total_re.findall(text)

    if amounts:
        try:
            valid_amounts = []
            for amt in amounts:
                clean_amt = amt.replace(',', '.').replace(' ', '')
                try:
                    val = float(clean_amt)
                    valid_amounts.append(val)
                except ValueError:
                    continue
            
            if valid_amounts:
                result["montant"] = max(valid_amounts)
        except Exception as e:
            logger.error(f"Error parsing amount: {e}")

    # 2. Find Date
    # Tesseract often messes up / or -
    date_re = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b')
    date_match = date_re.search(text)
    if date_match:
        try:
            day, month, year = date_match.groups()
            if len(year) == 2:
                year = "20" + year
            result["date"] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        except Exception:
            pass
            
    # 3. Find Supplier (Heuristic)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if lines:
        potential_supplier = lines[0]
        common_headers = ["facture", "ticket", "recu", "cb", "duplicata", "total", "date", "merci"]
        if len(potential_supplier) > 3 and not any(h in potential_supplier.lower() for h in common_headers):
             result["fournisseur"] = potential_supplier
        elif len(lines) > 1:
             potential_supplier = lines[1]
             if len(potential_supplier) > 3:
                 result["fournisseur"] = potential_supplier

    return result
