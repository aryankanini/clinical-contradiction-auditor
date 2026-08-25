#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('dev.db')
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print("Tables:", [t[0] for t in tables])
print()

# Search for the audit-only string in all text columns
target_text = "Audit-only output"
for table_name in [t[0] for t in tables]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    text_columns = [col[1] for col in columns if 'text' in col[2].lower() or 'json' in col[2].lower()]
    
    if text_columns:
        for col in text_columns:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {col} LIKE ?", (f"%{target_text}%",))
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"Found {count} matches in {table_name}.{col}")
                    cursor.execute(f"SELECT {col} FROM {table_name} WHERE {col} LIKE ?", (f"%{target_text}%",))
                    for row in cursor.fetchall():
                        print(f"  Value: {row[0][:100]}...")
            except:
                pass

conn.close()
