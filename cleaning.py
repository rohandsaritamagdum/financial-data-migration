import re
from datetime import datetime
from decimal import Decimal

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
TYPE_ALIASES = {"CREDIT": "CREDIT", "CR": "CREDIT", "DEBIT": "DEBIT", "DR": "DEBIT"}


def clean_text(value):
    """Remove spaces at the start and end, and collapse repeated spaces."""
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value):
    """Turn text into a real date. Return None if it is not a real date."""
    text = clean_text(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def parse_amount(value):
    """Turn text like '1,200.50' into a number. Return None if it is not a number."""
    text = clean_text(value).replace(",", "").replace("$", "")
    try:
        return Decimal(text)
    except Exception:
        return None


def normalize_type(value):
    """Turn 'dr', 'Dr', 'DR' into 'DEBIT'. Unknown words are kept (in capitals)."""
    key = clean_text(value).upper()
    return TYPE_ALIASES.get(key, key)