"""
News Collector - Indian News Auto-Collection
Primary Source  : NewsData.io  (free, real-time, India-focused)
Backup Source   : NewsAPI.org  (fallback)
Schedule        : Every 3 hours + 6 AM, 9 AM, 12 PM, 3 PM, 6 PM, 9 PM
Duplicate Check : URL hash + Content hash (title + date)
"""

import os
import requests
import time
import hashlib
import threading
import schedule
import random
from datetime import datetime, timedelta
from typing import List, Dict

# ─────────────────────────────────────────────────────────────
# SOURCE CREDIBILITY
# ─────────────────────────────────────────────────────────────

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
    'ANI': 0.8,
    'PTI': 0.85,
    'The Wire': 0.75,
    'Scroll.in': 0.75,
    'The Print': 0.78,
    'Deccan Herald': 0.78,
    'Mint': 0.82,
}

QUESTIONABLE_SOURCES = {
    'Unknown': 0.3,
    'Social Media': 0.2,
    '[Removed]': 0.0,
}

# NewsData.io categories for India
NEWSDATA_CATEGORIES = [
    "top", "politics", "business", "technology",
    "health", "sports", "entertainment", "science", "world"
]


class IndianNewsCollector:
    """
    Dual-source news collector.
    NewsData.io is the PRIMARY source (free + real-time India news).
    NewsAPI.org is the FALLBACK source.
    """

    def __init__(self, api_key: str, database, impact_generator=None):
        self.newsapi_key = api_key          # NewsAPI.org key (from .env NEWS_API_KEY)
        self.database = database
        self.impact_generator = impact_generator

        # NewsData.io API key — read from .env
        self.newsdata_key = os.getenv("NEWSDATA_API_KEY", "")

        # NewsAPI endpoints
        self.newsapi_headlines = "https://newsapi.org/v2/top-headlines"
        self.newsapi_everything = "https://newsapi.org/v2/everything"

        # NewsData.io endpoint
        self.newsdata_url = "https://newsdata.io/api/1/news"

        print("✅ News Collector initialised")
        if self.newsdata_key:
            print("   📡 Primary source: NewsData.io (real-time India news)")
        else:
            print("   ⚠️  NewsData.io key not set — using NewsAPI.org only")
            print("   💡 Get free key at https://newsdata.io  → add NEWSDATA_API_KEY to .env")
        print("   📡 Backup source : NewsAPI.org")

    # ─────────────────────────────────────────────────────────
    # NEWSDATA.IO  (PRIMARY — best for India, real-time)
    # ─────────────────────────────────────────────────────────

    def fetch_newsdata(self, category: str = "top", page: str = None) -> List[Dict]:
        """
        Fetch from NewsData.io.
        Free plan: 200 results/request, real-time, India-specific.
        Returns list of articles normalized to NewsAPI format.
        """
        if not self.newsdata_key:
            return []

        params = {
            "apikey": self.newsdata_key,
            "country": "in",
            "language": "en",
            "category": category,
        }
        if page:
            params["page"] = page

        try:
            response = requests.get(self.newsdata_url, params=params, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    raw_articles = data.get("results", [])
                    # Normalize to common format
                    articles = [self._normalize_newsdata(a) for a in raw_articles if a.get("title")]
                    print(f"  ✅ NewsData.io [{category}]: {len(articles)} articles")
                    return articles
                else:
                    print(f"  ⚠️  NewsData.io status: {data.get('status')} — {data.get('message','')}")
            elif response.status_code == 422:
                print(f"  ⚠️  NewsData.io: Invalid category '{category}' — skipping")
            elif response.status_code == 429:
                print(f"  ⚠️  NewsData.io: Rate limit hit — waiting 60s")
                time.sleep(60)
            else:
                print(f"  ❌ NewsData.io HTTP {response.status_code}")

        except Exception as e:
            print(f"  ❌ NewsData.io fetch error: {e}")

        return []

    def _normalize_newsdata(self, article: Dict) -> Dict:
        """Convert NewsData.io article format to our standard format"""
        return {
            "title": article.get("title", ""),
            "description": article.get("description") or article.get("content", ""),
            "content": article.get("content", ""),
            "url": article.get("link", ""),
            "publishedAt": article.get("pubDate", ""),
            "source": {"name": article.get("source_id", "NewsData.io").replace("-", " ").title()},
            "urlToImage": article.get("image_url", ""),
        }

    # ─────────────────────────────────────────────────────────
    # NEWSAPI.ORG  (FALLBACK)
    # ─────────────────────────────────────────────────────────

    def fetch_newsapi_headlines(self, category: str = "general", page_size: int = 20, page: int = 1) -> List[Dict]:
        """Fetch top headlines from NewsAPI.org"""
        params = {
            "country": "in",
            "category": category,
            "pageSize": page_size,
            "page": page,
            "apiKey": self.newsapi_key
        }
        try:
            response = requests.get(self.newsapi_headlines, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    articles = data.get("articles", [])
                    print(f"  ✅ NewsAPI headlines [{category}]: {len(articles)} articles")
                    return articles
            elif response.status_code == 426:
                # Free plan upgrade required — try /everything
                return self._fetch_newsapi_everything(category, page_size)
            elif response.status_code == 429:
                print(f"  ⚠️  NewsAPI rate limit — waiting 60s")
                time.sleep(60)
            else:
                print(f"  ❌ NewsAPI HTTP {response.status_code} [{category}]")
        except Exception as e:
            print(f"  ❌ NewsAPI fetch error: {e}")
        return []

    def _fetch_newsapi_everything(self, category: str, page_size: int = 20) -> List[Dict]:
        """Fallback: /everything endpoint with today's date filter"""
        category_queries = {
            "general":       "india news",
            "politics":      "india politics parliament",
            "business":      "india economy sensex startup",
            "technology":    "india tech AI digital",
            "health":        "india health hospital",
            "sports":        "india cricket IPL",
            "entertainment": "bollywood india",
            "science":       "india ISRO space",
        }
        query = category_queries.get(category, "india")
        from_date = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')

        params = {
            "q": query,
            "from": from_date,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": self.newsapi_key
        }
        try:
            response = requests.get(self.newsapi_everything, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    articles = data.get("articles", [])
                    print(f"  ✅ NewsAPI everything [{category}]: {len(articles)} articles")
                    return articles
            elif response.status_code == 429:
                print(f"  ⚠️  NewsAPI rate limit — waiting 60s")
                time.sleep(60)
        except Exception as e:
            print(f"  ❌ NewsAPI everything error: {e}")
        return []

    # ─────────────────────────────────────────────────────────
    # SMART DUPLICATE DETECTION
    # ─────────────────────────────────────────────────────────

    def _make_content_hash(self, title: str, published_at: str) -> str:
        """Hash based on normalized title + publish date — catches mirrors/syndicated duplicates"""
        normalized = ''.join(c.lower() for c in title if c.isalnum() or c.isspace()).strip()
        date_part = published_at[:10] if published_at else ""
        return hashlib.md5(f"{normalized}|{date_part}".encode()).hexdigest()

    def _is_duplicate(self, url: str, title: str, published_at: str) -> bool:
        if self.database.is_url_exists(url):
            return True
        content_hash = self._make_content_hash(title, published_at)
        if self.database.is_content_hash_exists(content_hash):
            return True
        return False

    # ─────────────────────────────────────────────────────────
    # ARTICLE VERIFICATION
    # ─────────────────────────────────────────────────────────

    def get_source_credibility(self, source_name: str) -> float:
        if source_name in TRUSTED_SOURCES:
            return TRUSTED_SOURCES[source_name]
        elif source_name in QUESTIONABLE_SOURCES:
            return QUESTIONABLE_SOURCES[source_name]
        return 0.5

    def verify_article(self, article: Dict, model, vectorizer) -> Dict:
        from utils.preprocess import clean_text, short_text
        from utils.claim_type import detect_claim_type
        from utils.wiki_verify import wikipedia_verify

        title = article.get("title", "")
        description = article.get("description", "")
        content = article.get("content", "")
        source = article.get("source", {}).get("name", "Unknown")

        if title == "[Removed]" or not title:
            return {"result": "⚠️ NEEDS FACT CHECKING", "confidence": 0.0, "explanation": "Article removed"}

        text = f"{title} {description} {content}"
        source_trust = self.get_source_credibility(source)

        if wikipedia_verify(text):
            return {"result": "🟢 VERIFIED FACT", "confidence": 95.0, "explanation": "Verified using Wikipedia"}

        if detect_claim_type(text) == "HISTORICAL":
            return {"result": "🟢 VERIFIED FACT", "confidence": 95.0, "explanation": "Historical fact"}

        processed = clean_text(short_text(text))
        vec = vectorizer.transform([processed])
        probs = model.predict_proba(vec)[0]
        ml_confidence = round(max(probs) * 100, 2)
        ml_label = model.classes_[probs.argmax()]
        combined = (ml_confidence * 0.7) + (source_trust * 100 * 0.3)

        if combined < 60:
            return {"result": "⚠️ NEEDS FACT CHECKING", "confidence": round(combined, 2),
                    "explanation": f"Uncertain (Source: {source})"}
        elif ml_label == 1:
            return {"result": "🟢 REAL NEWS", "confidence": round(combined, 2),
                    "explanation": f"ML prediction (trust: {source_trust:.2f})"}
        else:
            if source_trust > 0.8 and combined < 85:
                return {"result": "⚠️ NEEDS FACT CHECKING", "confidence": round(combined, 2),
                        "explanation": "Trusted source flagged — needs review"}
            return {"result": "🔴 FAKE NEWS", "confidence": round(combined, 2),
                    "explanation": f"ML prediction (trust: {source_trust:.2f})"}

    # ─────────────────────────────────────────────────────────
    # AI IMPACTS
    # ─────────────────────────────────────────────────────────

    def generate_ai_impacts(self, headline: str, description: str, is_fake: bool):
        if not self.impact_generator:
            return None
        try:
            print(f"   🤖 Generating AI impacts...")
            impacts = (self.impact_generator.generate_fake_news_impact(headline, description)
                       if is_fake else
                       self.impact_generator.generate_real_news_impact(headline, description))
            print(f"   ✅ AI impacts done")
            return impacts
        except Exception as e:
            print(f"   ⚠️  AI impact failed: {e}")
            return None

    # ─────────────────────────────────────────────────────────
    # PROCESS & STORE
    # ─────────────────────────────────────────────────────────

    def process_and_store_articles(self, articles: List[Dict], model, vectorizer):
        stored_count = 0
        fake_count = 0
        duplicate_count = 0

        # De-duplicate within current batch by URL
        seen_urls = set()
        unique_batch = []
        for a in articles:
            url = a.get("url", "")
            if url and url not in seen_urls:
                unique_batch.append(a)
                seen_urls.add(url)

        print(f"\n📦 Processing {len(unique_batch)} unique articles...")

        for article in unique_batch:
            try:
                title       = article.get("title", "")
                description = article.get("description", "") or ""
                source      = article.get("source", {}).get("name", "Unknown")
                url         = article.get("url", "")
                published_at = article.get("publishedAt", "")

                if not title or title == "[Removed]" or not url:
                    continue

                # Smart duplicate check
                if self._is_duplicate(url, title, published_at):
                    duplicate_count += 1
                    continue

                content_hash = self._make_content_hash(title, published_at)

                # Verify
                verification = self.verify_article(article, model, vectorizer)
                is_fake = "FAKE" in verification["result"]

                # AI impacts
                ai_impacts = self.generate_ai_impacts(title, description, is_fake)

                # Store
                success = self.database.add_auto_collected_news(
                    headline=title,
                    description=description,
                    source=source,
                    url=url,
                    published_at=published_at,
                    result=verification["result"],
                    confidence=verification["confidence"],
                    ai_impacts=ai_impacts,
                    content_hash=content_hash
                )

                if success:
                    stored_count += 1
                    if is_fake:
                        fake_count += 1
                        print(f"  🚨 FAKE : {title[:70]}...")
                    else:
                        print(f"  ✅ REAL : {title[:70]}...")
                else:
                    duplicate_count += 1

                time.sleep(1.2 if ai_impacts else 0.3)

            except Exception as e:
                print(f"  ❌ Error processing article: {e}")

        self.database.add_collection_stats(
            fetched=len(articles),
            stored=stored_count,
            duplicates=duplicate_count,
            fake=fake_count
        )

        print(f"\n📊 Summary → Total: {len(articles)} | Unique batch: {len(unique_batch)} | "
              f"NEW stored: {stored_count} | Duplicates skipped: {duplicate_count} | Fake: {fake_count}")

        return stored_count, fake_count

    # ─────────────────────────────────────────────────────────
    # MAIN COLLECTION — called by scheduler
    # ─────────────────────────────────────────────────────────

    def collect_daily_news(self, model, vectorizer):
        print(f"\n{'='*65}")
        print(f"🗞️  Auto News Collection — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*65}")

        all_articles = []

        # ── STEP 1: NewsData.io (primary — free, real-time India) ──────
        if self.newsdata_key:
            print("\n📡 Step 1: NewsData.io (primary source)...")
            for category in NEWSDATA_CATEGORIES:
                articles = self.fetch_newsdata(category=category)
                all_articles.extend(articles)
                time.sleep(0.8)   # Respect rate limit
        else:
            print("\n⚠️  Step 1: SKIPPED — No NEWSDATA_API_KEY found")
            print("   👉 Get free key: https://newsdata.io  (200 articles/request, real-time)")

        # ── STEP 2: NewsAPI.org (backup) ───────────────────────────────
        print("\n📡 Step 2: NewsAPI.org (backup source)...")
        newsapi_categories = ["general", "business", "technology", "health", "sports", "entertainment"]
        for category in newsapi_categories:
            articles = self.fetch_newsapi_headlines(category=category, page_size=20)
            if not articles:
                articles = self._fetch_newsapi_everything(category, page_size=15)
            all_articles.extend(articles)
            time.sleep(0.5)

        print(f"\n📚 Total raw articles collected: {len(all_articles)}")

        if not all_articles:
            print("⚠️  No articles collected — check API keys and quotas")
            return 0, 0

        # ── STEP 3: Verify, generate impacts, store ────────────────────
        print("\n🤖 Step 3: Verifying & storing with AI impact generation...")
        stored, fake = self.process_and_store_articles(all_articles, model, vectorizer)

        print(f"\n✅ Done! {stored} new articles stored | {fake} fake detected\n")
        return stored, fake


# ─────────────────────────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────────────────────────

def schedule_news_collection(collector, model, vectorizer):
    def job():
        try:
            print(f"\n⏰ Scheduled collection at {datetime.now().strftime('%H:%M:%S')}")
            collector.collect_daily_news(model, vectorizer)
        except Exception as e:
            print(f"❌ Scheduled job failed: {e}")

    schedule.every(3).hours.do(job)
    for t in ["06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]:
        schedule.every().day.at(t).do(job)

    print("📅 Schedule: Every 3h + 6 AM / 9 AM / 12 PM / 3 PM / 6 PM / 9 PM")

    # Run immediately on startup
    print("🚀 Running initial collection on startup...")
    job()

    while True:
        schedule.run_pending()
        time.sleep(60)


def start_news_collector_thread(collector, model, vectorizer):
    thread = threading.Thread(
        target=schedule_news_collection,
        args=(collector, model, vectorizer),
        daemon=True
    )
    thread.start()
    print("✅ News collector background thread started")
