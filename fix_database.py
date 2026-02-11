"""
QUICK FIX - Database Schema Issue
Choose your preferred solution
"""

import os
import sqlite3
import shutil
from datetime import datetime

DB_PATH = "news_records.db"

print("="*60)
print("DATABASE SCHEMA FIX")
print("="*60)

if not os.path.exists(DB_PATH):
    print("\n✅ No existing database - you can just run: python app.py")
    exit(0)

print(f"\n📂 Found existing database: {DB_PATH}")

# Get database size
db_size = os.path.getsize(DB_PATH) / 1024  # KB
print(f"   Size: {db_size:.2f} KB")

# Count records
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM auto_collected_news")
    auto_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM news_records")
    records_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"   Auto-collected news: {auto_count}")
    print(f"   User submissions: {records_count}")
    
except Exception as e:
    print(f"   Could not read database: {e}")
    auto_count = 0
    records_count = 0

print("\n" + "="*60)
print("CHOOSE YOUR SOLUTION:")
print("="*60)

print("\n1️⃣  OPTION 1: Fresh Start (RECOMMENDED)")
print("   - Deletes old database")
print("   - Creates new database with correct schema")
print("   - Loses old auto-collected news (but you can re-collect)")
print("   - Keeps your code and models")

print("\n2️⃣  OPTION 2: Migrate Existing Data")
print("   - Keeps all existing data")
print("   - Adds missing columns and constraints")
print("   - May remove duplicate URLs")
print("   - Takes longer but preserves history")

print("\n" + "="*60)

choice = input("\nEnter 1 or 2 (or 'q' to quit): ").strip()

if choice == '1':
    print("\n🗑️  OPTION 1 SELECTED: Fresh Start")
    print("="*60)
    
    # Create backup
    if auto_count > 0 or records_count > 0:
        backup_name = f"news_records.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        print(f"\n📦 Creating backup: {backup_name}")
        shutil.copy2(DB_PATH, backup_name)
        print(f"✅ Backup created (just in case)")
    
    # Delete old database
    print(f"\n🗑️  Deleting old database...")
    os.remove(DB_PATH)
    print("✅ Old database deleted")
    
    print("\n" + "="*60)
    print("✅ DONE! Now run:")
    print("   python app.py")
    print("="*60)
    print("\nThe app will create a fresh database with:")
    print("   ✅ Duplicate prevention")
    print("   ✅ All new features")
    print("   ✅ Clean schema")
    
elif choice == '2':
    print("\n🔧 OPTION 2 SELECTED: Migrate Existing Data")
    print("="*60)
    print("\nRunning migration script...")
    print()
    
    # Import and run migration
    os.system("python migrate_database.py")
    
elif choice.lower() == 'q':
    print("\n❌ Cancelled")
    
else:
    print("\n❌ Invalid choice")

print()