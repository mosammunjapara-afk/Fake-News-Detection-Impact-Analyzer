import os
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict
import schedule
import threading
import random

# Source credibility scores
TRUSTED_SOURCES = {
    'Business Standard': 0.9,
    'The Times of India': 0.85,
    'The Hindu': 0.9,
    'Economic Times': 0.85,
    'NDTV': 0.8,
    'India Today': 0.8,
    'Hindustan Times': 0.8,
    'The Indian Express': 0.85,
    'News18': 0.75,
    'CNBC-TV18': 0.8,
}

QUESTIONABLE_SOURCES = {
    'Unknown': 0.3,
    'Social Media': 0.2,
    '[Removed]': 0.0,
}

class IndianNewsCollector:
    """Enhanced news collector with AI impact generation"""
    
    def __init__(self, api_key: str, database, impact_generator=None):
        self.api_key = api_key
        self.database = database
        self.impact_generator = impact_generator  # AI impact generator
        self.base_url_headlines = "https://newsapi.org/v2/top-headlines"
        self.base_url_everything = "https://newsapi.org/v2/everything"
        self.categories = ["general", "politics", "business", "technology", "health", "sports", "entertainment"]
        self.current_page = 1
        self.max_page = 5
        
    def fetch_indian_news(self, category: str = "general", page_size: int = 20, page: int = 1) -> List[Dict]:
        """Fetch latest news with pagination support"""
        articles = []
        
        # Try top-headlines first
        params = {
            "country": "in",
            "category": category,
            "pageSize": page_size,
            "page": page,
            "apiKey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url_headlines, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    articles = data.get("articles", [])
                    if articles:
                        print(f"✅ Fetched {len(articles)} articles from {category} (page {page})")
                    else:
                        articles = self._fetch_everything_endpoint(category, page_size, page)
            elif response.status_code == 429:
                print(f"❌ Rate limit exceeded for {category}")
            elif response.status_code == 426:
                print(f"⚠️ Top-headlines requires upgrade, using 'everything' endpoint...")
                articles = self._fetch_everything_endpoint(category, page_size, page)
            else:
                print(f"❌ Error {response.status_code} for {category}")
                articles = self._fetch_everything_endpoint(category, page_size, page)
                
        except Exception as e:
            print(f"❌ Error fetching news: {e}")
            articles = self._fetch_everything_endpoint(category, page_size, page)
        
        return articles
    
    def _fetch_everything_endpoint(self, category: str, page_size: int, page: int = 1) -> List[Dict]:
        """Fetch from everything endpoint with time-based freshness"""
        
        time_windows = [
            {"hours": 6, "label": "last 6 hours"},
            {"hours": 12, "label": "last 12 hours"},
            {"hours": 24, "label": "last 24 hours"},
            {"hours": 48, "label": "last 48 hours"},
        ]
        
        window = time_windows[page % len(time_windows)]
        
        category_queries = {
            "general": "india OR delhi OR mumbai OR bangalore OR chennai",
            "politics": "india politics OR modi OR parliament OR election",
            "business": "india economy OR sensex OR nifty OR startup india",
            "technology": "india tech OR IT india OR AI india OR coding india",
            "health": "india health OR covid india OR ayurveda OR healthcare",
            "sports": "india cricket OR IPL OR kohli OR olympics india",
            "entertainment": "bollywood OR indian cinema OR OTT india"
        }
        
        query = category_queries.get(category, "india")
        from_date = (datetime.now() - timedelta(hours=window["hours"])).strftime('%Y-%m-%dT%H:%M:%S')
        
        params = {
            "q": query,
            "from": from_date,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "page": page,
            "apiKey": self.api_key
        }
        
        try:
            response = requests.get(self.base_url_everything, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    articles = data.get("articles", [])
                    print(f"✅ Fetched {len(articles)} articles from 'everything' ({category}, {window['label']}, page {page})")
                    return articles
            else:
                print(f"❌ Everything endpoint error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error with everything endpoint: {e}")
        
        return []
    
    def get_source_credibility(self, source_name: str) -> float:
        """Get credibility score for a news source"""
        if source_name in TRUSTED_SOURCES:
            return TRUSTED_SOURCES[source_name]
        elif source_name in QUESTIONABLE_SOURCES:
            return QUESTIONABLE_SOURCES[source_name]
        else:
            return 0.5
    
    def verify_article(self, article: Dict, model, vectorizer) -> Dict:
        """Verify an article using enhanced multi-stage verification"""
        from utils.preprocess import clean_text, short_text
        from utils.claim_type import detect_claim_type
        from utils.wiki_verify import wikipedia_verify
        
        title = article.get("title", "")
        description = article.get("description", "")
        content = article.get("content", "")
        source = article.get("source", {}).get("name", "Unknown")
        
        if title == "[Removed]" or not title:
            return {
                "result": "⚠️ NEEDS FACT CHECKING",
                "confidence": 0.0,
                "explanation": "Article removed or unavailable"
            }
        
        text = f"{title} {description} {content}"
        source_trust = self.get_source_credibility(source)
        
        # Wikipedia verification
        if wikipedia_verify(text):
            return {
                "result": "🟢 VERIFIED FACT",
                "confidence": 95.0,
                "explanation": "Verified using Wikipedia"
            }
        
        # Claim type detection
        claim_type = detect_claim_type(text)
        
        if claim_type == "HISTORICAL":
            return {
                "result": "🟢 VERIFIED FACT",
                "confidence": 95.0,
                "explanation": "Historical fact"
            }
        
        # ML prediction
        processed = clean_text(short_text(text))
        vec = vectorizer.transform([processed])
        probs = model.predict_proba(vec)[0]
        
        ml_confidence = round(max(probs) * 100, 2)
        ml_label = model.classes_[probs.argmax()]
        
        # Combine ML + source trust
        combined_confidence = (ml_confidence * 0.7) + (source_trust * 100 * 0.3)
        
        # Final decision
        if combined_confidence < 60:
            result = "⚠️ NEEDS FACT CHECKING"
            explanation = f"Uncertain prediction (Source: {source})"
        elif ml_label == 1:
            result = "🟢 REAL NEWS"
            explanation = f"ML prediction (Source trust: {source_trust:.2f})"
        else:
            if source_trust > 0.8:
                if combined_confidence < 85:
                    result = "⚠️ NEEDS FACT CHECKING"
                    explanation = f"Trusted source flagged - needs review"
                else:
                    result = "🔴 FAKE NEWS"
                    explanation = f"High confidence fake (trusted source)"
            else:
                result = "🔴 FAKE NEWS"
                explanation = f"ML prediction (Source trust: {source_trust:.2f})"
        
        return {
            "result": result,
            "confidence": round(combined_confidence, 2),
            "explanation": explanation
        }
    
    def generate_ai_impacts(self, headline: str, description: str, is_fake: bool) -> List[Dict]:
        """Generate AI impacts for the article"""
        if not self.impact_generator:
            return None
        
        try:
            print(f"   🤖 Generating AI impacts...")
            if is_fake:
                impacts = self.impact_generator.generate_fake_news_impact(headline, description)
            else:
                impacts = self.impact_generator.generate_real_news_impact(headline, description)
            print(f"   ✅ AI impacts generated successfully")
            return impacts
        except Exception as e:
            print(f"   ⚠️ AI impact generation failed: {e}")
            return None
    
    def process_and_store_articles(self, articles: List[Dict], model, vectorizer):
        """Process articles with AI impact generation and store"""
        stored_count = 0
        fake_count = 0
        needs_review_count = 0
        duplicate_count = 0
        
        for article in articles:
            try:
                title = article.get("title", "")
                description = article.get("description", "")
                source = article.get("source", {}).get("name", "Unknown")
                url = article.get("url", "")
                published_at = article.get("publishedAt", "")
                
                if not title or title == "[Removed]" or not url:
                    continue
                
                # Check if URL already exists
                if self.database.is_url_exists(url):
                    duplicate_count += 1
                    continue
                
                # Verify article
                verification = self.verify_article(article, model, vectorizer)
                
                # Determine if fake
                is_fake = "FAKE" in verification["result"]
                
                # Generate AI impacts for this specific article
                ai_impacts = self.generate_ai_impacts(title, description, is_fake)
                
                # Store in database with AI impacts
                success = self.database.add_auto_collected_news(
                    headline=title,
                    description=description or "",
                    source=source,
                    url=url,
                    published_at=published_at,
                    result=verification["result"],
                    confidence=verification["confidence"],
                    ai_impacts=ai_impacts
                )
                
                if success:
                    stored_count += 1
                    
                    if is_fake:
                        fake_count += 1
                        print(f"🚨 FAKE: {title[:60]}... (AI impacts generated)")
                    elif "NEEDS FACT CHECKING" in verification["result"]:
                        needs_review_count += 1
                    else:
                        print(f"✅ REAL: {title[:60]}... (AI impacts generated)")
                else:
                    duplicate_count += 1
                
                # Small delay to avoid API rate limits
                if ai_impacts:
                    time.sleep(1)
                
            except Exception as e:
                print(f"Error processing article: {e}")
        
        # Store collection statistics
        self.database.add_collection_stats(
            fetched=len(articles),
            stored=stored_count,
            duplicates=duplicate_count,
            fake=fake_count
        )
        
        print(f"\n📊 Summary: Fetched: {len(articles)} | New: {stored_count} | Duplicates: {duplicate_count} | Fake: {fake_count}")
        
        return stored_count, fake_count
    
    def collect_daily_news(self, model, vectorizer, use_pagination: bool = True):
        """Enhanced collection with AI impact generation"""
        print(f"\n{'='*60}")
        print(f"🤖 AI-Powered News Collection - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
        
        all_articles = []
        
        # Rotate through pages for variety
        if use_pagination:
            current_page = random.randint(1, 3)
        else:
            current_page = 1
        
        # Shuffle categories for variety
        categories = self.categories.copy()
        random.shuffle(categories)
        
        for category in categories[:5]:
            print(f"📰 Fetching {category} news (page {current_page})...")
            articles = self.fetch_indian_news(
                category=category, 
                page_size=20,
                page=current_page
            )
            all_articles.extend(articles)
            time.sleep(1)
        
        # Remove duplicates within batch
        unique_articles = []
        seen_urls = set()
        
        for article in all_articles:
            url = article.get("url", "")
            if url and url not in seen_urls:
                unique_articles.append(article)
                seen_urls.add(url)
        
        print(f"\n📚 Unique articles in batch: {len(unique_articles)}")
        
        if len(unique_articles) == 0:
            print("⚠️ No articles collected")
            return 0, 0
        
        print(f"\n🤖 Starting AI impact generation for each article...")
        stored, fake = self.process_and_store_articles(unique_articles, model, vectorizer)
        
        print(f"\n✅ Collection completed! Stored {stored} articles with AI-generated impacts\n")
        return stored, fake


def schedule_news_collection(collector, model, vectorizer):
    """Schedule automatic collection every 3 hours"""
    
    def job():
        try:
            collector.collect_daily_news(model, vectorizer, use_pagination=True)
        except Exception as e:
            print(f"❌ Collection job failed: {e}")
    
    schedule.every(3).hours.do(job)
    schedule.every().day.at("06:00").do(job)
    schedule.every().day.at("09:00").do(job)
    schedule.every().day.at("12:00").do(job)
    schedule.every().day.at("15:00").do(job)
    schedule.every().day.at("18:00").do(job)
    schedule.every().day.at("21:00").do(job)
    
    print("📅 Scheduled: Every 3 hours + 6 AM, 9 AM, 12 PM, 3 PM, 6 PM, 9 PM")
    print("🤖 AI impact generation enabled for all articles")
    
    print("🚀 Running initial collection with AI impacts...")
    job()
    
    while True:
        schedule.run_pending()
        time.sleep(60)


def start_news_collector_thread(collector, model, vectorizer):
    """Start news collector in background thread"""
    thread = threading.Thread(
        target=schedule_news_collection,
        args=(collector, model, vectorizer),
        daemon=True
    )
    thread.start()
    print("✅ News collector thread started - AI impacts for every article!")