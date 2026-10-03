# import sqlite3

# conn = sqlite3.connect("chatbot.db")
# cursor = conn.cursor()

# cursor.execute("ALTER TABLE api_keys ADD COLUMN user_id TEXT;")
# conn.commit()
# conn.close()


import sqlite3

# Connect to your existing DB
conn = sqlite3.connect("chatbot.db")
cursor = conn.cursor()

# Add new columns if they don't already exist
# (SQLite doesn't support "IF NOT EXISTS" in ALTER TABLE directly,
#  so we'll check manually)
def add_column_if_missing(table, column, col_type):
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [info[1] for info in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type};")
        print(f"✅ Added column '{column}' to '{table}'")
    else:
        print(f"⚠️ Column '{column}' already exists in '{table}'")

# --- Existing migration example ---
add_column_if_missing("api_keys", "user_id", "TEXT")

# --- Add Subscription-related fields ---
add_column_if_missing("subscriptions", "openai_api_key", "TEXT")
add_column_if_missing("subscriptions", "pinecone_api_key", "TEXT")
add_column_if_missing("subscriptions", "pinecone_env", "TEXT")
add_column_if_missing("subscriptions", "pinecone_index", "TEXT")

# Normalize legacy plan values so SQLAlchemy can load PlanEnum (single-tier app)
cursor.execute(
    """
    UPDATE subscriptions
    SET plan = 'free_trial'
    WHERE plan IN ('shared', 'dedicated', 'blackbox', 'black_box')
    """
)
if cursor.rowcount:
    print(f"✅ Normalized {cursor.rowcount} subscription plan row(s) to free_trial")
else:
    print("⚠️ No legacy subscription plans to normalize (or column empty)")

# --- project_uploads.doc_id (for RAG delete from dashboard) ---
cursor.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='project_uploads';"
)
if cursor.fetchone():
    add_column_if_missing("project_uploads", "doc_id", "TEXT")

# Commit and close
conn.commit()
conn.close()

print("✅ Migration completed successfully!")
