"""
Unit conversion utilities
"""
def kwh_to_mwh(kwh: float) -> float:
    return kwh / 1000.0

def litres_to_kl(litres: float) -> float:
    return litres / 1000.0

def kg_to_tonnes(kg: float) -> float:
    return kg / 1000.0

def inr_to_lakh(inr: float) -> float:
    return inr / 100000.0
