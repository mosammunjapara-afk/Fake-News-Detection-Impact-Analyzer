import re

def contains_future_tense(text: str) -> bool:
    """Check if text contains future tense indicators"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Future indicators
    future_patterns = [
        r'\bwill\b',
        r'\bgoing to\b',
        r'\bshall\b',
        r'\bplans to\b',
        r'\bexpects to\b',
        r'\bintends to\b',
        r'\bscheduled to\b',
        r'\bto be\s+\w+ed\b',  # "to be launched"
        r'\bupcoming\b',
        r'\bnext (week|month|year)\b',
        r'\bin (the )?(future|coming days|near future)\b',
        r'\bsoon\b',
        r'\bahead\b'
    ]
    
    for pattern in future_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False