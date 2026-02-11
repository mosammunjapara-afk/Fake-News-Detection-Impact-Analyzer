import re

def detect_claim_type(text: str) -> str:
    """Detect the type of claim"""
    if not text:
        return "GENERAL"
    
    text_lower = text.lower()
    
    # Historical facts - years, dates, historical events
    historical_patterns = [
        r'\b(19|20)\d{2}\b',  # Years like 1947, 2020
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+(19|20)\d{2}\b',
        r'\b(born|died|founded|established|independence|war|battle|signed|passed)\b',
        r'\b(was|were|had been|became)\b.*\b(first|second|third|last)\b',
        r'\b(history|historical|ancient|medieval|century|era|period)\b'
    ]
    
    for pattern in historical_patterns:
        if re.search(pattern, text_lower):
            return "HISTORICAL"
    
    # Policy/Government claims
    policy_keywords = [
        'government', 'policy', 'minister', 'prime minister', 'president',
        'parliament', 'bill', 'law', 'regulation', 'scheme', 'yojana',
        'budget', 'tax', 'amendment', 'cabinet', 'announced', 'launches',
        'ministry', 'department', 'official', 'statement'
    ]
    
    if any(keyword in text_lower for keyword in policy_keywords):
        return "POLICY"
    
    return "GENERAL"