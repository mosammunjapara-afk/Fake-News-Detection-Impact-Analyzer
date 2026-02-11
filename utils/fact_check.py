import requests

def google_fact_check(text: str, api_key: str) -> dict:
    """Check claim using Google Fact Check API"""
    if not api_key or not text:
        return None
    
    try:
        url = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
        params = {
            "query": text[:200],
            "key": api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("claims"):
                claim = data["claims"][0]
                claim_review = claim.get("claimReview", [{}])[0]
                
                return {
                    "rating": claim_review.get("textualRating", "Unknown"),
                    "publisher": claim_review.get("publisher", {}).get("name", "Unknown"),
                    "url": claim_review.get("url", "")
                }
        
        return None
        
    except Exception as e:
        print(f"Fact check error: {e}")
        return None