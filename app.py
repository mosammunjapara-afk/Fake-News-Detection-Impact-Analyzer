import os
import joblib
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from utils.preprocess import clean_text, short_text
from utils.claim_type import detect_claim_type
from utils.fact_check import google_fact_check
from utils.wiki_verify import wikipedia_verify
from utils.temporal import contains_future_tense

from database import NewsDatabase
from news_collector import IndianNewsCollector, start_news_collector_thread
from impact_generator import ImpactGenerator

load_dotenv()

app = Flask(__name__)

# Load ML model
model = joblib.load("model/model.pkl")
vectorizer = joblib.load("model/vectorizer.pkl")

# API Keys
GOOGLE_FACT_API_KEY = os.getenv("GOOGLE_FACT_API_KEY")
NEWS_API_KEY        = os.getenv("NEWS_API_KEY")
NEWSDATA_API_KEY    = os.getenv("NEWSDATA_API_KEY")   # NEW: NewsData.io key

# Initialize database
db = NewsDatabase()

# Initialize AI Impact Generator
impact_gen = ImpactGenerator()

# Initialize news collector (works even if only one key is present)
news_collector = IndianNewsCollector(NEWS_API_KEY or "", db, impact_gen)
start_news_collector_thread(news_collector, model, vectorizer)
print("✅ Automatic news collection enabled")
print("📅 Collection schedule: Every 3 hours + 6 AM, 9 AM, 12 PM, 3 PM, 6 PM, 9 PM")


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    confidence = None
    explanation = None
    claim_type = None

    if request.method == "POST":
        user_text = request.form["news"]
        ip_address = request.remote_addr

        # Wikipedia verification
        if wikipedia_verify(user_text):
            result = "🟢 VERIFIED FACT"
            explanation = "Verified using Wikipedia knowledge base."
            confidence = 95.0
            claim_type = "VERIFIED"

        # Future tense guardrail
        elif contains_future_tense(user_text):
            result = "⚠️ NEEDS OFFICIAL VERIFICATION"
            explanation = "Future or planned events require official confirmation."
            confidence = 50.0
            claim_type = "FUTURE"

        else:
            claim_type_detected = detect_claim_type(user_text)

            # Historical facts
            if claim_type_detected == "HISTORICAL":
                result = "🟢 VERIFIED FACT"
                explanation = "This is a well-established historical fact."
                confidence = 95.0
                claim_type = "HISTORICAL"

            # Policy claims
            elif claim_type_detected == "POLICY":
                fact = google_fact_check(user_text, GOOGLE_FACT_API_KEY)

                if fact:
                    result = f"🟢 VERIFIED ({fact['rating']})"
                    explanation = f"Source: {fact['publisher']}"
                    confidence = 90.0
                    claim_type = "POLICY"
                else:
                    result = "⚠️ NEEDS OFFICIAL VERIFICATION"
                    explanation = "Policy-related claim requires official confirmation."
                    confidence = 50.0
                    claim_type = "POLICY"

            # General claims → ML
            else:
                processed = clean_text(short_text(user_text))
                vec = vectorizer.transform([processed])
                probs = model.predict_proba(vec)[0]

                confidence = round(max(probs) * 100, 2)
                label = model.classes_[probs.argmax()]

                if confidence < 70:
                    result = "⚠️ NEEDS FACT CHECKING"
                    explanation = "Claim is ambiguous or lacks strong evidence. Model confidence is low."
                    claim_type = "AMBIGUOUS"
                else:
                    result = "🟢 REAL NEWS" if label == 1 else "🔴 FAKE NEWS"
                    explanation = f"ML prediction based on model confidence of {confidence}%"
                    claim_type = "GENERAL"

        # Store in database
        db.add_news_record(
            news_text=user_text,
            result=result,
            confidence=confidence,
            explanation=explanation,
            claim_type=claim_type,
            source="User Submission",
            ip_address=ip_address
        )

    return render_template(
        "index.html",
        result=result,
        confidence=confidence,
        explanation=explanation
    )


@app.route("/dashboard")
def dashboard():
    """Dashboard showing all fake news detections"""
    
    filter_type = request.args.get('filter', 'all')
    days = int(request.args.get('days', 7))
    
    stats = db.get_statistics(days=days)
    fake_news = db.get_recent_fake_news(limit=100, days=days)
    
    if filter_type == 'fake':
        all_records = db.get_all_news_records(limit=100, filter_type='fake')
    elif filter_type == 'real':
        all_records = db.get_all_news_records(limit=100, filter_type='real')
    else:
        all_records = db.get_all_news_records(limit=100)
    
    return render_template(
        "dashboard.html",
        stats=stats,
        fake_news=fake_news,
        all_records=all_records,
        filter_type=filter_type,
        days=days
    )


@app.route("/auto-collected")
def auto_collected():
    """View automatically collected news with AI-generated impacts"""
    
    auto_news = db.get_auto_collected_news(limit=200)
    
    fake_auto = [n for n in auto_news if "FAKE" in (n.get('result') or '')]
    real_auto = [n for n in auto_news if "REAL" in (n.get('result') or '') or "VERIFIED" in (n.get('result') or '')]
    
    return render_template(
        "auto_collected.html",
        auto_news=auto_news,
        fake_count=len(fake_auto),
        real_count=len(real_auto),
        total_count=len(auto_news)
    )


@app.route("/api/generate-impact", methods=["POST"])
def generate_impact():
    """API endpoint to generate AI-powered impact analysis on-demand"""
    try:
        data = request.json
        headline = data.get('headline', '')
        description = data.get('description', '')
        is_fake = data.get('is_fake', False)
        
        if is_fake:
            impacts = impact_gen.generate_fake_news_impact(headline, description)
        else:
            impacts = impact_gen.generate_real_news_impact(headline, description)
        
        return jsonify({
            'status': 'success',
            'impacts': impacts
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route("/api/stats")
def api_stats():
    """API endpoint for statistics"""
    days = int(request.args.get('days', 7))
    stats = db.get_statistics(days=days)
    return jsonify(stats)


@app.route("/api/collection-stats")
def api_collection_stats():
    """API endpoint for collection statistics"""
    stats = db.get_collection_stats(limit=10)
    
    total_duplicates = sum(stat['duplicates_skipped'] for stat in stats)
    total_fetched = sum(stat['articles_fetched'] for stat in stats)
    total_stored = sum(stat['articles_stored'] for stat in stats)
    
    return jsonify({
        'recent_collections': stats,
        'total_duplicates': total_duplicates,
        'total_fetched': total_fetched,
        'total_stored': total_stored
    })


@app.route("/api/trigger-collection")
def trigger_collection():
    """Manually trigger news collection with AI impact generation"""
    if NEWS_API_KEY:
        try:
            print("\n🔄 Manual collection triggered from web interface...")
            stored, fake = news_collector.collect_daily_news(model, vectorizer)
            return jsonify({
                "status": "success",
                "stored": stored,
                "fake_detected": fake,
                "message": f"Collected {stored} articles with AI-generated impacts"
            })
        except Exception as e:
            print(f"❌ Collection error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    else:
        return jsonify({"status": "error", "message": "NEWS_API_KEY not configured"}), 400


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 Fake News Detection System with AI Impact Analysis")
    print("="*70)
    print("📊 Features:")
    print("   ✅ Auto news collection every 3 hours")
    print("   ✅ Duplicate prevention (URL-based)")
    print("   ✅ Multi-source verification")
    print("   ✅ ML-powered fake news detection")
    print("   ✅ AI-generated unique impacts for EVERY article")
    print("   ✅ Impacts stored in database permanently")
    print("="*70 + "\n")
    
    app.run(debug=True, threaded=True)

@app.route("/api/force-refresh", methods=["POST"])
def force_refresh():
    """Force fetch TODAY's fresh news — called from UI button"""
    try:
        print("\n🔄 FORCE REFRESH triggered from UI...")
        stored, fake = news_collector.collect_daily_news(model, vectorizer)
        return jsonify({
            "status": "success",
            "stored": stored,
            "fake_detected": fake,
            "message": f"Fetched {stored} new articles ({fake} fake detected)"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/clear-old-news", methods=["POST"])
def clear_old_news():
    """Delete articles older than N days"""
    try:
        data = request.json or {}
        days = int(data.get("days", 3))
        deleted = db.delete_old_news(days=days)
        return jsonify({
            "status": "success",
            "deleted": deleted,
            "message": f"Deleted {deleted} articles older than {days} days"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/news-status")
def news_status():
    """Returns latest collection info for the UI status bar"""
    try:
        stats  = db.get_collection_stats(limit=1)
        latest = stats[0] if stats else None
        recent = db.get_auto_collected_news(limit=1)
        newest = recent[0]['collected_at'] if recent else "Never"
        return jsonify({
            "status": "ok",
            "last_collection":          latest['collection_time'] if latest else "Never",
            "newest_article":           newest,
            "articles_stored_last_run": latest['articles_stored'] if latest else 0,
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
