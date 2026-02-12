import sqlite3
from datetime import datetime
from typing import List, Dict
import json
import hashlib


class NewsDatabase:
    def __init__(self, db_path: str = "news_records.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ── news_records ──────────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                news_text TEXT NOT NULL,
                result TEXT NOT NULL,
                confidence REAL,
                explanation TEXT,
                claim_type TEXT,
                source TEXT,
                ip_address TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_fake BOOLEAN,
                country TEXT DEFAULT 'India'
            )
        ''')

        # ── auto_collected_news (base schema — extra cols added by migration) ──
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auto_collected_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                headline TEXT NOT NULL,
                description TEXT,
                source TEXT,
                url TEXT UNIQUE NOT NULL,
                published_at DATETIME,
                result TEXT,
                confidence REAL,
                collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                url_hash TEXT,
                ai_impacts TEXT
            )
        ''')

        # Index on url_hash
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_url_hash
            ON auto_collected_news(url_hash)
        ''')

        # ── daily_stats ───────────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                total_checked INTEGER DEFAULT 0,
                fake_detected INTEGER DEFAULT 0,
                real_detected INTEGER DEFAULT 0,
                avg_confidence REAL
            )
        ''')

        # ── collection_stats ──────────────────────────────────────────
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                articles_fetched INTEGER,
                articles_stored INTEGER,
                duplicates_skipped INTEGER,
                fake_detected INTEGER
            )
        ''')

        conn.commit()

        # Safely add any new columns to existing databases
        self._migrate_if_needed(conn)

        conn.close()

    def _migrate_if_needed(self, conn):
        """
        Safely add new columns to existing databases.
        Uses ALTER TABLE only if the column does not already exist.
        This prevents the 'no such column' crash on old databases.
        """
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(auto_collected_news)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        # Add ai_impacts if missing
        if 'ai_impacts' not in existing_columns:
            try:
                cursor.execute('ALTER TABLE auto_collected_news ADD COLUMN ai_impacts TEXT')
                conn.commit()
                print("✅ DB migrated: added ai_impacts column")
            except Exception as e:
                print(f"⚠️  Migration note (ai_impacts): {e}")

        # Add content_hash if missing
        if 'content_hash' not in existing_columns:
            try:
                cursor.execute('ALTER TABLE auto_collected_news ADD COLUMN content_hash TEXT')
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_content_hash
                    ON auto_collected_news(content_hash)
                ''')
                conn.commit()
                print("✅ DB migrated: added content_hash column")
            except Exception as e:
                print(f"⚠️  Migration note (content_hash): {e}")

    # ──────────────────────────────────────────────────────────────────
    # USER SUBMISSION RECORDS
    # ──────────────────────────────────────────────────────────────────

    def add_news_record(self, news_text: str, result: str, confidence: float,
                        explanation: str, claim_type: str = None,
                        source: str = "User Submission", ip_address: str = None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        is_fake = "FAKE" in result.upper() or "🔴" in result
        cursor.execute('''
            INSERT INTO news_records
            (news_text, result, confidence, explanation, claim_type, source, ip_address, is_fake)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (news_text, result, confidence, explanation, claim_type, source, ip_address, is_fake))
        conn.commit()
        conn.close()
        self.update_daily_stats()

    # ──────────────────────────────────────────────────────────────────
    # AUTO-COLLECTED NEWS
    # ──────────────────────────────────────────────────────────────────

    def add_auto_collected_news(self, headline: str, description: str, source: str,
                                url: str, published_at: str, result: str, confidence: float,
                                ai_impacts: List[Dict] = None, content_hash: str = None):
        """Add auto-collected news with AI-generated impacts and duplicate prevention"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        url_hash = hashlib.md5(url.encode()).hexdigest()
        impacts_json = json.dumps(ai_impacts) if ai_impacts else None

        try:
            cursor.execute('''
                INSERT INTO auto_collected_news
                (headline, description, source, url, published_at, result, confidence,
                 url_hash, ai_impacts, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (headline, description, source, url, published_at, result, confidence,
                  url_hash, impacts_json, content_hash))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Duplicate URL
        finally:
            conn.close()

    def is_url_exists(self, url: str) -> bool:
        """Check if URL already exists by URL or url_hash"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cursor.execute('''
            SELECT COUNT(*) FROM auto_collected_news
            WHERE url_hash = ? OR url = ?
        ''', (url_hash, url))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def is_content_hash_exists(self, content_hash: str) -> bool:
        """Check if a similar article (same normalized title + date) already exists"""
        if not content_hash:
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM auto_collected_news
                WHERE content_hash = ?
            ''', (content_hash,))
            count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            # content_hash column not yet present — safe fallback
            count = 0
        conn.close()
        return count > 0

    # ──────────────────────────────────────────────────────────────────
    # QUERY METHODS
    # ──────────────────────────────────────────────────────────────────

    def get_recent_fake_news(self, limit: int = 50, days: int = 30) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT news_text, result, confidence, explanation, timestamp, source
            FROM news_records
            WHERE is_fake = 1 AND timestamp >= datetime('now', '-' || ? || ' days')
            ORDER BY timestamp DESC LIMIT ?
        ''', (days, limit))
        records = []
        for row in cursor.fetchall():
            records.append({
                'text': row[0], 'result': row[1], 'confidence': row[2],
                'explanation': row[3], 'timestamp': row[4], 'source': row[5]
            })
        conn.close()
        return records

    def get_all_news_records(self, limit: int = 100, filter_type: str = None) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = 'SELECT * FROM news_records'
        params = []
        if filter_type == 'fake':
            query += ' WHERE is_fake = 1'
        elif filter_type == 'real':
            query += ' WHERE is_fake = 0'
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        cursor.execute(query, params)
        records = []
        for row in cursor.fetchall():
            records.append({
                'id': row[0], 'text': row[1], 'result': row[2], 'confidence': row[3],
                'explanation': row[4], 'claim_type': row[5], 'source': row[6],
                'ip_address': row[7], 'timestamp': row[8], 'is_fake': row[9], 'country': row[10]
            })
        conn.close()
        return records

    def get_auto_collected_news(self, limit: int = 200) -> List[Dict]:
        """Get auto-collected news ordered by newest first"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, headline, description, source, url, published_at,
                   result, confidence, collected_at, ai_impacts
            FROM auto_collected_news
            ORDER BY collected_at DESC LIMIT ?
        ''', (limit,))
        records = []
        for row in cursor.fetchall():
            ai_impacts = None
            if row[9]:
                try:
                    ai_impacts = json.loads(row[9])
                except Exception:
                    ai_impacts = None
            records.append({
                'id': row[0], 'headline': row[1], 'description': row[2],
                'source': row[3], 'url': row[4], 'published_at': row[5],
                'result': row[6], 'confidence': row[7], 'collected_at': row[8],
                'ai_impacts': ai_impacts
            })
        conn.close()
        return records

    def add_collection_stats(self, fetched: int, stored: int, duplicates: int, fake: int):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO collection_stats
            (articles_fetched, articles_stored, duplicates_skipped, fake_detected)
            VALUES (?, ?, ?, ?)
        ''', (fetched, stored, duplicates, fake))
        conn.commit()
        conn.close()

    def get_collection_stats(self, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM collection_stats
            ORDER BY collection_time DESC LIMIT ?
        ''', (limit,))
        stats = []
        for row in cursor.fetchall():
            stats.append({
                'id': row[0], 'collection_time': row[1],
                'articles_fetched': row[2], 'articles_stored': row[3],
                'duplicates_skipped': row[4], 'fake_detected': row[5]
            })
        conn.close()
        return stats

    def update_daily_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        today = datetime.now().date()
        cursor.execute('''
            SELECT COUNT(*), SUM(CASE WHEN is_fake = 1 THEN 1 ELSE 0 END),
                   SUM(CASE WHEN is_fake = 0 THEN 1 ELSE 0 END), AVG(confidence)
            FROM news_records WHERE DATE(timestamp) = ?
        ''', (today,))
        row = cursor.fetchone()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_stats
            (date, total_checked, fake_detected, real_detected, avg_confidence)
            VALUES (?, ?, ?, ?, ?)
        ''', (today, row[0] or 0, row[1] or 0, row[2] or 0, row[3] or 0))
        conn.commit()
        conn.close()

    def get_statistics(self, days: int = 7) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT SUM(total_checked), SUM(fake_detected), SUM(real_detected), AVG(avg_confidence)
            FROM daily_stats WHERE date >= date('now', '-' || ? || ' days')
        ''', (days,))
        row = cursor.fetchone()
        stats = {
            'total_checked': row[0] or 0,
            'fake_detected': row[1] or 0,
            'real_detected': row[2] or 0,
            'avg_confidence': round(row[3] or 0, 2)
        }
        conn.close()
        return stats

    def delete_old_news(self, days: int = 3) -> int:
        """Delete auto-collected articles older than N days. Returns count deleted."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM auto_collected_news
            WHERE collected_at < datetime('now', '-' || ? || ' days')
        ''', (days,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        print(f"🗑️  Deleted {deleted} articles older than {days} days")
        return deleted
