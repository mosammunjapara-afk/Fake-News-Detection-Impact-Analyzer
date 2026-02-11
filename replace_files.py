"""
Automatic File Replacement Script
Replaces old files with new fresh news versions
"""

import os
import shutil
from datetime import datetime

print("="*60)
print("FRESH NEWS SYSTEM - FILE REPLACEMENT")
print("="*60)

# Check if new files exist
files_to_replace = [
    {
        'old': 'news_collector.py',
        'new': 'news_collector_fresh.py',
        'backup': f'news_collector_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.py'
    },
    {
        'old': 'templates/auto_collected.html',
        'new': 'templates/auto_collected_fresh.html',
        'backup': f'templates/auto_collected_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    }
]

print("\n📋 Files to Replace:")
for item in files_to_replace:
    print(f"   {item['old']} → {item['new']}")

print("\n" + "="*60)
choice = input("Continue with replacement? (y/n): ").strip().lower()

if choice != 'y':
    print("❌ Cancelled")
    exit(0)

print("\n🔄 Starting Replacement...")

for item in files_to_replace:
    old_file = item['old']
    new_file = item['new']
    backup_file = item['backup']
    
    # Check if new file exists
    if not os.path.exists(new_file):
        print(f"⚠️  {new_file} not found - skipping")
        continue
    
    # Backup old file if it exists
    if os.path.exists(old_file):
        print(f"\n📦 Backing up {old_file}...")
        try:
            shutil.copy2(old_file, backup_file)
            print(f"   ✅ Backup created: {backup_file}")
        except Exception as e:
            print(f"   ❌ Backup failed: {e}")
            continue
    
    # Replace with new file
    print(f"🔄 Replacing {old_file}...")
    try:
        if os.path.exists(old_file):
            os.remove(old_file)
        shutil.copy2(new_file, old_file)
        print(f"   ✅ {old_file} updated!")
    except Exception as e:
        print(f"   ❌ Replacement failed: {e}")
        
        # Restore backup if replacement failed
        if os.path.exists(backup_file):
            print(f"   🔙 Restoring backup...")
            shutil.copy2(backup_file, old_file)

print("\n" + "="*60)
print("✅ REPLACEMENT COMPLETE!")
print("="*60)

print("\nUpdated Files:")
print("   ✅ news_collector.py - Fresh news with pagination")
print("   ✅ templates/auto_collected.html - Auto-refresh UI")

print("\n📋 Backup Files Created:")
for item in files_to_replace:
    if os.path.exists(item['backup']):
        print(f"   📦 {item['backup']}")

print("\n🚀 Next Steps:")
print("   1. Run: python app.py")
print("   2. Visit: http://127.0.0.1:5000/auto-collected")
print("   3. Click: 'Collect Fresh News Now'")
print("   4. Enable: 'Auto-refresh every 5 min' checkbox")

print("\n🎉 Features:")
print("   ✅ News collected every 3 hours")
print("   ✅ Different articles each time (pagination)")
print("   ✅ Auto-refresh option")
print("   ✅ Latest news shown first")
print("   ✅ New articles highlighted")

print("\n" + "="*60)