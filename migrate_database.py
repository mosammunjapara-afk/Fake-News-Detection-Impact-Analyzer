"""
Database Migration Script
Adds missing columns and tables to existing database
"""

import sqlite3
import os

DB_PATH = "news_records.db"

print("="*60)
print("DATABASE MIGRATION - Adding New Features")
print("="*60)

if not os.path.exists(DB_PATH):
    print(f"\n✅ No existing database found - will be created fresh")
    print("   Just run: python app.py")
    exit(0)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print(f"\n📂 Found existing database: {DB_PATH}")

# Check current schema
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='auto_collected_news'")
result = cursor.fetchone()

if result:
    current_schema = result[0]
    print(f"\n📋 Current auto_collected_news schema:")
    print(current_schema)
    
    # Check if url_hash column exists
    if 'url_hash' not in current_schema:
        print("\n⚠️  Missing url_hash column - adding it now...")
        
        try:
            # Add url_hash column
            cursor.execute('ALTER TABLE auto_collected_news ADD COLUMN url_hash TEXT')
            print("✅ Added url_hash column")
            
            # Create index on url_hash
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_hash ON auto_collected_news(url_hash)')
            print("✅ Created url_hash index")
            
            # Populate url_hash for existing records
            import hashlib
            cursor.execute('SELECT id, url FROM auto_collected_news WHERE url IS NOT NULL')
            rows = cursor.fetchall()
            
            for row_id, url in rows:
                url_hash = hashlib.md5(url.encode()).hexdigest()
                cursor.execute('UPDATE auto_collected_news SET url_hash = ? WHERE id = ?', (url_hash, row_id))
            
            print(f"✅ Updated url_hash for {len(rows)} existing records")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error adding column: {e}")
            conn.rollback()
    else:
        print("\n✅ url_hash column already exists")
    
    # Make URL unique if not already
    print("\n🔒 Checking URL uniqueness constraint...")
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='auto_collected_news'")
    schema = cursor.fetchone()[0]
    
    if 'UNIQUE' not in schema or 'url' not in schema.split('UNIQUE')[0]:
        print("⚠️  URL column is not unique - recreating table with UNIQUE constraint...")
        
        try:
            # Create new table with UNIQUE constraint
            cursor.execute('''
                CREATE TABLE auto_collected_news_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    headline TEXT NOT NULL,
                    description TEXT,
                    source TEXT,
                    url TEXT UNIQUE NOT NULL,
                    published_at DATETIME,
                    result TEXT,
                    confidence REAL,
                    collected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    url_hash TEXT
                )
            ''')
            print("✅ Created new table with UNIQUE constraint")
            
            # Copy data, skipping duplicates
            cursor.execute('''
                INSERT OR IGNORE INTO auto_collected_news_new 
                (id, headline, description, source, url, published_at, result, confidence, collected_at, url_hash)
                SELECT id, headline, description, source, url, published_at, result, confidence, collected_at, url_hash
                FROM auto_collected_news
                WHERE url IS NOT NULL
            ''')
            
            rows_copied = cursor.rowcount
            print(f"✅ Copied {rows_copied} unique records")
            
            # Drop old table
            cursor.execute('DROP TABLE auto_collected_news')
            print("✅ Dropped old table")
            
            # Rename new table
            cursor.execute('ALTER TABLE auto_collected_news_new RENAME TO auto_collected_news')
            print("✅ Renamed new table")
            
            # Recreate index
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_url_hash ON auto_collected_news(url_hash)')
            print("✅ Recreated url_hash index")
            
            conn.commit()
            
        except Exception as e:
            print(f"❌ Error recreating table: {e}")
            conn.rollback()
    else:
        print("✅ URL column already has UNIQUE constraint")

else:
    print("\n⚠️  auto_collected_news table doesn't exist - will be created on first run")

# Create collection_stats table if it doesn't exist
print("\n📊 Checking collection_stats table...")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='collection_stats'")

if not cursor.fetchone():
    print("⚠️  collection_stats table missing - creating it...")
    
    try:
        cursor.execute('''
            CREATE TABLE collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                articles_fetched INTEGER,
                articles_stored INTEGER,
                duplicates_skipped INTEGER,
                fake_detected INTEGER
            )
        ''')
        
        conn.commit()
        print("✅ Created collection_stats table")
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        conn.rollback()
else:
    print("✅ collection_stats table exists")

conn.close()

print("\n" + "="*60)
print("✅ MIGRATION COMPLETE!")
print("="*60)
print("\nYou can now run your app:")
print("   python app.py")
print("="*60)