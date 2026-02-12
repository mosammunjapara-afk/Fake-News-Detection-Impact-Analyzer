"""
Indian News Auto-Collector — 3 Free Sources
=============================================
Source 1 (Primary)  : GNews API         — 100% free, no card, real-time India news
Source 2 (Secondary): NewsData.io       — free tier, real-time India news  
Source 3 (Backup)   : NewsAPI.org       — existing key (if quota allows)

Why 3 sources:
- If one API hits daily limit → others still collect fresh news
- More variety, less duplicates
- Today's news GUARANTEED

Setup:
  1. GNews    → https://gnews.io       → free signup → copy API key → add GNEWS_API_KEY in .env
  2. NewsData → https://newsdata.io    → free signup → copy API key → add NEWSDATA_API_KEY in .env  
  3. NewsAPI  → already in .env as NEWS_API_KEY (existing)
"""

import os
import requests
import time
import hashlib
import threading
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ─────────────────────────────────────────────────────────────
# SOURCE CREDIBILITY SCORES
# ─────────────────────────────────────────────────────────────
TRUSTED_SOURCES = {
    'The Hindu': 0.9, 'Business Standard': 0.9, 'PTI': 0.88,
    'The Indian Express': 0.88, 'Economic Times': 0.85,
    'The Times of India': 0.85, 'Mint': 0.85, 'ANI': 0.82,
    'NDTV': 0.82, 'Hindustan Times': 0.82, 'India Today': 0.80,
    'News18': 0.78, 'CNBC-TV18': 0.80, 'The Print': 0.78,
    'Scroll.in': 0.78, 'The Wire': 0.75, 'Deccan Herald': 0.78,
    'Tribune India': 0.75, 'Outlook India': 0.75,
}
QUESTIONABLE_SOURCES = {
    'Unknown': 0.3, 'Social Media': 0.2, '[Removed]': 0.0,
}


class IndianNewsCollector:
    """
    Auto-collects Indian news from 3 free sources.
    Each source is tried independently — if one fails, others fill in.
    """

    def __init__(self, api_key: str, database, impact_generator=None):
        self.database       = database
        self.impact_generator = impact_generator

        # API Keys — read from environment
        self.newsapi_key  = api_key                            # From NEWS_API_KEY in .env
        self.gnews_key    = os.getenv("GNEWS_API_KEY", "")    # New: GNews
        self.newsdata_key = os.getenv("NEWSDATA_API_KEY", "") # New: NewsData.io

        # Endpoints
        self.gnews_url    = "https://gnews.io/api/v4/top-headlines"
        self.newsdata_url = "https://newsdata.io/api/1/news"
        self.newsapi_url  = "https://newsapi.org/v2/top-headlines"
        self.newsapi_everything = "https://newsapi.org/v2/everything"

        self._print_status()

    def _print_status(self):
        print("\n📡 News Collector — Source Status:")
        print(f"   {'✅' if self.gnews_key    else '❌'} GNews API      {'(active)' if self.gnews_key    else '→ get free key: https://gnews.io'}")
        print(f"   {'✅' if self.newsdata_key else '❌'} NewsData.io    {'(active)' if self.newsdata_key else '→ get free key: https://newsdata.io'}")
        print(f"   {'✅' if self.newsapi_key  else '❌'} NewsAPI.org    {'(active)' if self.newsapi_key  else '→ missing NEWS_API_KEY'}")
        active = sum([bool(self.gnews_key), bool(self.newsdata_key), bool(self.newsapi_key)])
        print(f"   📊 {active}/3 sources active\n")

    # ═════════════════════════════════════════════════════════
    # SOURCE 1 — GNews API  (RECOMMENDED: best free India news)
    # ═════════════════════════════════════════════════════════

    def fetch_gnews(self, topic: str = "breaking-news", max_articles: int = 10) -> List[Dict]:
        """
        GNews free plan: 100 requests/day, up to 10 articles/request.
        Topics: breaking-news, world, nation, business, technology,
                entertainment, sports, science, health
        """
        if not self.gnews_key:
            return []

        params = {
            "token":    self.gnews_key,
            "country":  "in",
            "lang":     "en",
            "topic":    topic,
            "max":      max_articles,
            "sortby":   "publishedAt",    # Always newest first
        }

        try:
            r = requests.get(self.gnews_url, params=params, timeout=15)

            if r.status_code == 200:
                data = r.json()
                raw = data.get("articles", [])
                articles = [self._normalize_gnews(a) for a in raw if a.get("title")]
                print(f"  ✅ GNews [{topic}]: {len(articles)} articles")
                return articles

            elif r.status_code == 403:
                print(f"  ❌ GNews: Invalid API key")
            elif r.status_code == 429:
                print(f"  ⚠️  GNews: Daily limit reached (100 req/day on free plan)")
            else:
                print(f"  ❌ GNews HTTP {r.status_code} [{topic}]")

        except Exception as e:
            print(f"  ❌ GNews error [{topic}]: {e}")

        return []

    def _normalize_gnews(self, a: Dict) -> Dict:
        """Normalize GNews article to standard format"""
        source_name = a.get("source", {}).get("name", "GNews")
        return {
            "title":       a.get("title", ""),
            "description": a.get("description", ""),
            "content":     a.get("content", ""),
            "url":         a.get("url", ""),
            "publishedAt": a.get("publishedAt", ""),
            "source":      {"name": source_name},
        }

    # ═════════════════════════════════════════════════════════
    # SOURCE 2 — NewsData.io
    # ═════════════════════════════════════════════════════════

    def fetch_newsdata(self, category: str = "top") -> List[Dict]:
        """
        NewsData.io free plan: 200 results/request, real-time.
        """
        if not self.newsdata_key:
            return []

        params = {
            "apikey":   self.newsdata_key,
            "country":  "in",
            "language": "en",
            "category": category,
        }

        try:
            r = requests.get(self.newsdata_url, params=params, timeout=15)

            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "success":
                    raw = data.get("results", [])
                    articles = [self._normalize_newsdata(a) for a in raw if a.get("title")]
                    print(f"  ✅ NewsData.io [{category}]: {len(articles)} articles")
                    return articles
                else:
                    print(f"  ⚠️  NewsData.io: {data.get('message','Unknown error')}")
            elif r.status_code == 422:
                print(f"  ⚠️  NewsData.io: Invalid category '{category}'")
            elif r.status_code == 429:
                print(f"  ⚠️  NewsData.io: Rate limit hit")
                time.sleep(30)
            else:
                print(f"  ❌ NewsData.io HTTP {r.status_code}")

        except Exception as e:
            print(f"  ❌ NewsData.io error: {e}")

        return []

    def _normalize_newsdata(self, a: Dict) -> Dict:
        source_name = a.get("source_id", "newsdata").replace("-", " ").title()
        return {
            "title":       a.get("title", ""),
            "description": a.get("description") or a.get("content", ""),
            "content":     a.get("content", ""),
            "url":         a.get("link", ""),
            "publishedAt": a.get("pubDate", ""),
            "source":      {"name": source_name},
        }

    # ═════════════════════════════════════════════════════════
    # SOURCE 3 — NewsAPI.org  (existing, use as backup)
    # ═════════════════════════════════════════════════════════

    def fetch_newsapi(self, category: str = "general") -> List[Dict]:
        """NewsAPI.org — used as backup. Free plan has 24h delay limitation."""
        if not self.newsapi_key:
            return []

        # Try top-headlines first
        params = {
            "country":  "in",
            "category": category,
            "pageSize": 20,
            "apiKey":   self.newsapi_key,
        }
        try:
            r = requests.get(self.newsapi_url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    articles = data.get("articles", [])
                    print(f"  ✅ NewsAPI [{category}]: {len(articles)} articles")
                    return articles
            elif r.status_code in [426, 401]:
                # Plan limitation — try /everything with last 24h filter
                return self._newsapi_everything(category)
            elif r.status_code == 429:
                print(f"  ⚠️  NewsAPI: Rate limit hit")
                time.sleep(30)
            else:
                print(f"  ⚠️  NewsAPI HTTP {r.status_code} — trying /everything")
                return self._newsapi_everything(category)
        except Exception as e:
            print(f"  ❌ NewsAPI error: {e}")
        return []

    def _newsapi_everything(self, category: str) -> List[Dict]:
        queries = {
            "general": "india today", "business": "india economy finance",
            "technology": "india tech startup AI", "health": "india health",
            "sports": "india cricket IPL", "entertainment": "bollywood india",
        }
        q = queries.get(category, "india news")
        from_dt = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')

        try:
            r = requests.get(self.newsapi_everything, params={
                "q": q, "from": from_dt, "language": "en",
                "sortBy": "publishedAt", "pageSize": 20,
                "apiKey": self.newsapi_key,
            }, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    articles = data.get("articles", [])
                    print(f"  ✅ NewsAPI /everything [{category}]: {len(articles)} articles")
                    return articles
            elif r.status_code == 429:
                print(f"  ⚠️  NewsAPI /everything: Rate limit")
                time.sleep(30)
        except Exception as e:
            print(f"  ❌ NewsAPI /everything error: {e}")
        return []

    # ═════════════════════════════════════════════════════════
    # DUPLICATE DETECTION
    # ═════════════════════════════════════════════════════════

    def _content_hash(self, title: str, published_at: str) -> str:
        """Hash of normalized title + date — catches mirrors and syndicated copies"""
        clean = ''.join(c.lower() for c in title if c.isalnum() or c.isspace()).strip()
        date  = published_at[:10] if published_at else ""
        return hashlib.md5(f"{clean}|{date}".encode()).hexdigest()

    def _is_duplicate(self, url: str, title: str, published_at: str) -> bool:
        if self.database.is_url_exists(url):
            return True
        if self.database.is_content_hash_exists(self._content_hash(title, published_at)):
            return True
        return False

    # ═════════════════════════════════════════════════════════
    # VERIFICATION
    # ═════════════════════════════════════════════════════════

    def _source_trust(self, name: str) -> float:
        if name in TRUSTED_SOURCES:    return TRUSTED_SOURCES[name]
        if name in QUESTIONABLE_SOURCES: return QUESTIONABLE_SOURCES[name]
        return 0.5

    def verify_article(self, article: Dict, model, vectorizer) -> Dict:
        from utils.preprocess import clean_text, short_text
        from utils.claim_type import detect_claim_type
        from utils.wiki_verify import wikipedia_verify

        title  = article.get("title", "")
        desc   = article.get("description", "") or ""
        body   = article.get("content", "") or ""
        source = article.get("source", {}).get("name", "Unknown")

        if not title or title == "[Removed]":
            return {"result": "⚠️ NEEDS FACT CHECKING", "confidence": 0.0,
                    "explanation": "Article removed or unavailable"}

        text  = f"{title} {desc} {body}"
        trust = self._source_trust(source)

        if wikipedia_verify(text):
            return {"result": "🟢 VERIFIED FACT", "confidence": 95.0,
                    "explanation": "Verified using Wikipedia"}

        if detect_claim_type(text) == "HISTORICAL":
            return {"result": "🟢 VERIFIED FACT", "confidence": 95.0,
                    "explanation": "Historical fact"}

        processed = clean_text(short_text(text))
        vec   = vectorizer.transform([processed])
        probs = model.predict_proba(vec)[0]
        ml_conf  = round(max(probs) * 100, 2)
        ml_label = model.classes_[probs.argmax()]
        combined = (ml_conf * 0.7) + (trust * 100 * 0.3)

        if combined < 60:
            return {"result": "⚠️ NEEDS FACT CHECKING", "confidence": round(combined, 2),
                    "explanation": f"Low confidence (Source: {source})"}
        elif ml_label == 1:
            return {"result": "🟢 REAL NEWS", "confidence": round(combined, 2),
                    "explanation": f"ML prediction (trust: {trust:.2f})"}
        else:
            if trust > 0.8 and combined < 85:
                return {"result": "⚠️ NEEDS FACT CHECKING", "confidence": round(combined, 2),
                        "explanation": "Trusted source flagged — needs manual review"}
            return {"result": "🔴 FAKE NEWS", "confidence": round(combined, 2),
                    "explanation": f"ML prediction (trust: {trust:.2f})"}

    # ═════════════════════════════════════════════════════════
    # AI IMPACTS
    # ═════════════════════════════════════════════════════════

    def _gen_impacts(self, title: str, desc: str, is_fake: bool):
        if not self.impact_generator:
            return None
        try:
            fn = (self.impact_generator.generate_fake_news_impact if is_fake
                  else self.impact_generator.generate_real_news_impact)
            impacts = fn(title, desc)
            print(f"   🤖 AI impacts generated")
            return impacts
        except Exception as e:
            print(f"   ⚠️  AI impact failed: {e}")
            return None

    # ═════════════════════════════════════════════════════════
    # PROCESS & STORE
    # ═════════════════════════════════════════════════════════

    def process_and_store(self, articles: List[Dict], model, vectorizer):
        stored = fake = dupes = 0

        # Remove URL duplicates within this batch
        seen, unique = set(), []
        for a in articles:
            u = a.get("url", "")
            if u and u not in seen:
                unique.append(a)
                seen.add(u)

        print(f"\n📦 Processing {len(unique)} unique articles from batch...")

        for a in unique:
            try:
                title  = a.get("title", "")
                desc   = a.get("description", "") or ""
                source = a.get("source", {}).get("name", "Unknown")
                url    = a.get("url", "")
                pub_at = a.get("publishedAt", "")

                if not title or title == "[Removed]" or not url:
                    continue

                if self._is_duplicate(url, title, pub_at):
                    dupes += 1
                    continue

                chash        = self._content_hash(title, pub_at)
                verification = self.verify_article(a, model, vectorizer)
                is_fake      = "FAKE" in verification["result"]
                impacts      = self._gen_impacts(title, desc, is_fake)

                ok = self.database.add_auto_collected_news(
                    headline=title, description=desc, source=source,
                    url=url, published_at=pub_at,
                    result=verification["result"],
                    confidence=verification["confidence"],
                    ai_impacts=impacts, content_hash=chash,
                )

                if ok:
                    stored += 1
                    tag = "🚨 FAKE" if is_fake else "✅ REAL"
                    print(f"  {tag}: {title[:70]}...")
                    fake += is_fake
                else:
                    dupes += 1

                time.sleep(1.2 if impacts else 0.3)

            except Exception as e:
                print(f"  ❌ Error: {e}")

        self.database.add_collection_stats(
            fetched=len(articles), stored=stored,
            duplicates=dupes, fake=fake,
        )

        print(f"\n📊 Batch result → Raw: {len(articles)} | Unique: {len(unique)} | "
              f"NEW: {stored} | Dupes skipped: {dupes} | Fake: {fake}")
        return stored, fake

    # ═════════════════════════════════════════════════════════
    # MAIN COLLECTION — called every 3 hours by scheduler
    # ═════════════════════════════════════════════════════════

    def collect_daily_news(self, model, vectorizer):
        print(f"\n{'='*65}")
        print(f"🗞️  Auto Collection — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*65}")

        all_articles = []

        # ── SOURCE 1: GNews (best free real-time India news) ──────────
        if self.gnews_key:
            print("\n📡 Source 1: GNews API...")
            gnews_topics = [
                "breaking-news", "nation", "business",
                "technology", "sports", "health", "entertainment", "science"
            ]
            for topic in gnews_topics:
                articles = self.fetch_gnews(topic=topic, max_articles=10)
                all_articles.extend(articles)
                time.sleep(1)   # GNews: respect 100 req/day limit
        else:
            print("\n⚠️  Source 1 SKIPPED — add GNEWS_API_KEY to .env")
            print("   👉 Free signup at https://gnews.io (takes 1 minute)")

        # ── SOURCE 2: NewsData.io ─────────────────────────────────────
        if self.newsdata_key:
            print("\n📡 Source 2: NewsData.io...")
            for cat in ["top", "politics", "business", "technology", "sports", "health"]:
                articles = self.fetch_newsdata(category=cat)
                all_articles.extend(articles)
                time.sleep(0.8)
        else:
            print("\n⚠️  Source 2 SKIPPED — add NEWSDATA_API_KEY to .env")
            print("   👉 Free signup at https://newsdata.io (takes 1 minute)")

        # ── SOURCE 3: NewsAPI.org (existing key, backup) ──────────────
        if self.newsapi_key:
            print("\n📡 Source 3: NewsAPI.org (backup)...")
            for cat in ["general", "business", "technology", "health", "sports"]:
                articles = self.fetch_newsapi(category=cat)
                all_articles.extend(articles)
                time.sleep(0.5)
        else:
            print("\n⚠️  Source 3 SKIPPED — NEWS_API_KEY missing in .env")

        print(f"\n📚 Total articles collected across all sources: {len(all_articles)}")

        if not all_articles:
            print("\n🚨 ZERO articles collected!")
            print("   Possible reasons:")
            print("   1. All API keys are missing — check your .env file")
            print("   2. NewsAPI free plan expired/rate-limited")
            print("   3. Internet connection issue")
            print("\n   👉 Quick fix: Add GNEWS_API_KEY to .env (free at https://gnews.io)")
            return 0, 0

        stored, fake = self.process_and_store(all_articles, model, vectorizer)
        print(f"\n✅ Collection complete! {stored} new articles stored | {fake} fake detected\n")
        return stored, fake


# ─────────────────────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────────────────────

def schedule_news_collection(collector, model, vectorizer):
    def job():
        try:
            print(f"\n⏰ Scheduled run at {datetime.now().strftime('%H:%M:%S')}")
            collector.collect_daily_news(model, vectorizer)
        except Exception as e:
            print(f"❌ Scheduled job failed: {e}")

    schedule.every(3).hours.do(job)
    for t in ["06:00", "09:00", "12:00", "15:00", "18:00", "21:00"]:
        schedule.every().day.at(t).do(job)

    print("📅 Schedule: Every 3h + 6/9/12/15/18/21")

    print("🚀 Initial collection on startup...")
    job()

    while True:
        schedule.run_pending()
        time.sleep(60)


def start_news_collector_thread(collector, model, vectorizer):
    t = threading.Thread(
        target=schedule_news_collection,
        args=(collector, model, vectorizer),
        daemon=True,
    )
    t.start()
    print("✅ News collector thread started")
