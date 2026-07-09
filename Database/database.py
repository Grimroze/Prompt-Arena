import psycopg2
import os
from dotenv import load_dotenv

# Load env variables so we can read SUPABASE_DB_URL
load_dotenv()

DB_URL = os.environ.get("SUPABASE_DB_URL")

def init_db():
    """Create the Evaluations table if it doesn't exist."""
    if not DB_URL:
        print("SUPABASE_DB_URL not set. Skipping DB initialization.")
        return
        
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Evaluations (
                id SERIAL PRIMARY KEY,
                session_id TEXT,
                query TEXT,
                prompt_a TEXT,
                prompt_b TEXT,
                code_a TEXT,
                code_b TEXT,
                winner TEXT,
                score_a REAL,
                score_b REAL,
                latency_a REAL,
                latency_b REAL,
                tokens_a INTEGER,
                tokens_b INTEGER,
                cost_a REAL,
                cost_b REAL,
                confidence REAL,
                reason TEXT,
                evaluated_by TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database initialization failed: {e}")

def save_evaluation(result: dict, session_id: str):
    """Save the evaluation result into the database."""
    if not DB_URL:
        print("SUPABASE_DB_URL not set. Skipping save.")
        return
        
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO Evaluations (
                session_id, query, prompt_a, prompt_b, 
                code_a, code_b,
                winner, score_a, score_b, 
                latency_a, latency_b, 
                tokens_a, tokens_b, 
                cost_a, cost_b, 
                confidence, reason, evaluated_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            session_id,
            result.get("query"),
            result.get("prompt_a"),
            result.get("prompt_b"),
            result.get("code", {}).get("A", ""),
            result.get("code", {}).get("B", ""),
            result.get("winner"),
            result.get("scores", {}).get("A"),
            result.get("scores", {}).get("B"),
            result.get("latency", {}).get("A"),
            result.get("latency", {}).get("B"),
            result.get("tokens", {}).get("A"),
            result.get("tokens", {}).get("B"),
            result.get("cost", {}).get("A"),
            result.get("cost", {}).get("B"),
            result.get("confidence"),
            result.get("reason"),
            result.get("evaluated_by")
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to save evaluation: {e}")

def get_recent_evaluations(limit=10):
    """Fetch the most recent evaluations from the database."""
    if not DB_URL:
        print("SUPABASE_DB_URL not set. Cannot fetch history.")
        return []
        
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * 
            FROM Evaluations 
            ORDER BY timestamp DESC 
            LIMIT %s
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        # Convert tuples to list of dictionaries
        results = [dict(zip(columns, row)) for row in rows]
        return results
    except Exception as e:
        print(f"Failed to fetch recent evaluations: {e}")
        return []
