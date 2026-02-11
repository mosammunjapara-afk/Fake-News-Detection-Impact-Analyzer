try:
    import wikipedia
    WIKIPEDIA_AVAILABLE = True
except ImportError:
    WIKIPEDIA_AVAILABLE = False

def wikipedia_verify(text: str, threshold: int = 3) -> bool:
    """Verify text against Wikipedia"""
    if not WIKIPEDIA_AVAILABLE or not text:
        return False
    
    try:
        # Search Wikipedia
        search_results = wikipedia.search(text[:100], results=3)
        
        if not search_results:
            return False
        
        # Try to get page content
        for result in search_results[:2]:
            try:
                page = wikipedia.page(result, auto_suggest=False)
                
                # Check if text content overlaps with Wikipedia page
                text_lower = text.lower()
                page_content_lower = page.content.lower()
                
                # Simple word overlap check
                text_words = set(text_lower.split()[:50])
                page_words = set(page_content_lower.split()[:500])
                
                overlap = len(text_words & page_words)
                
                if overlap >= threshold:
                    return True
                    
            except (wikipedia.exceptions.DisambiguationError, 
                    wikipedia.exceptions.PageError):
                continue
        
        return False
        
    except Exception:
        return False