import asyncio
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import duckdb
import gradio as gr
from fastapi import FastAPI, Query, Response
import uvicorn

# ── Config ──────────────────────────────────────────────────────────────
REMOTE_URL = "https://huggingface.co/datasets/sauravsingh2111/Tgdata/resolve/main/TELEGRAM_MASTER_DB.parquet"
PARALLELISM = int(os.environ.get("TG_PARALLEL", "2"))
THREADS_PER_CONN = int(os.environ.get("TG_THREADS_PER_CONN", "2"))

# ── DuckDB Connection ──────────────────────────────────────────────────
_conns = []
_conns_lock = threading.Lock()
_thread_local = threading.local()
pool = ThreadPoolExecutor(max_workers=PARALLELISM)

def _new_conn():
    con = duckdb.connect()
    con.execute("SET home_directory='/tmp'")
    con.execute("SET extension_directory='/tmp/duckdb_extensions'")
    con.execute("INSTALL parquet; LOAD parquet;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET threads = {THREADS_PER_CONN}")
    
    # Create view
    con.execute(f"""
        CREATE OR REPLACE VIEW tg_data AS 
        SELECT * FROM read_parquet('{REMOTE_URL}')
    """)
    
    # Detect columns (for debugging)
    try:
        cols = con.execute("SELECT * FROM tg_data LIMIT 1").fetchall()
        if cols:
            col_names = [d[0] for d in con.description]
            print(f"✅ Columns detected: {col_names}")
    except Exception as e:
        print(f"⚠️ Column detection failed: {e}")
    
    return con

def _get_conn():
    ident = getattr(_thread_local, "id", None)
    if ident is None:
        with _conns_lock:
            ident = len(_conns)
            _thread_local.id = ident
    with _conns_lock:
        while len(_conns) <= ident:
            _conns.append(_new_conn())
    return _conns[ident]

# ── Search ──────────────────────────────────────────────────────────────
def _search(q: str, limit: int = 10):
    q = q.strip()
    if not q:
        return {"query": q, "count": 0, "results": []}
    
    con = _get_conn()
    
    # First, get column names
    try:
        sample = con.execute("SELECT * FROM tg_data LIMIT 1").fetchall()
        if not sample:
            return {"query": q, "count": 0, "results": [], "error": "No data in dataset"}
        columns = [d[0] for d in con.description]
        print(f"🔍 Columns: {columns}")
    except Exception as e:
        return {"query": q, "count": 0, "results": [], "error": f"Failed to read data: {str(e)}"}
    
    # Build search queries dynamically based on available columns
    search_queries = []
    
    # Phone number (if column exists)
    if 'phoneNumber' in columns and q.isdigit() and len(q) >= 8:
        search_queries.append(("phoneNumber", f"= '{q}'"))
    
    # Username (if column exists)
    if 'username' in columns:
        search_queries.append(("username", f"ILIKE '%{q}%'"))
    
    # Name (if column exists)
    if 'name' in columns:
        search_queries.append(("name", f"ILIKE '%{q}%'"))
    
    # If no specific columns, try any text column
    if not search_queries:
        for col in columns:
            if col not in ['phoneNumber', 'username', 'name']:
                search_queries.append((col, f"ILIKE '%{q}%'"))
                break
    
    # Execute searches
    for field, condition in search_queries:
        try:
            sql = f"SELECT * FROM tg_data WHERE {field} {condition} LIMIT {limit + 5}"
            rows = con.execute(sql).fetchall()
            if rows:
                cols = [d[0] for d in con.description]
                results = [dict(zip(cols, r)) for r in rows][:limit]
                return {"query": q, "count": len(results), "results": results, "searched_in": field}
        except Exception as e:
            print(f"⚠️ Search failed for {field}: {e}")
            continue
    
    return {"query": q, "count": 0, "results": [], "message": "No results found"}

# ── FastAPI ──────────────────────────────────────────────────────────────
fastapi_app = FastAPI(
    title="Telegram Search API",
    description="🚀 Built by @SOCIALBANNERR | Channel: @modxpatel"
)

@fastapi_app.get("/")
def root():
    return {
        "app": "Telegram Search API",
        "developer": "@SOCIALBANNERR",
        "channel": "@modxpatel",
        "dataset": "sauravsingh2111/Tgdata",
        "status": "active"
    }

@fastapi_app.get("/health")
def health():
    try:
        con = _get_conn()
        con.execute("SELECT 1").fetchall()
        return {"status": "ok", "db": "connected", "developer": "@SOCIALBANNERR"}
    except Exception as e:
        return {"status": "error", "db": f"failed: {str(e)}", "developer": "@SOCIALBANNERR"}

@fastapi_app.get("/search")
async def search(q: str = Query(...), limit: int = Query(10, ge=1, le=100)):
    loop = asyncio.get_running_loop()
    try:
        data = await loop.run_in_executor(pool, _search, q, limit)
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type="application/json"
        )
    except Exception as e:
        error_response = {
            "query": q,
            "error": str(e),
            "developer": "@SOCIALBANNERR"
        }
        return Response(
            content=json.dumps(error_response, indent=2),
            media_type="application/json",
            status_code=500
        )

# ── Gradio UI ──────────────────────────────────────────────────────────
def search_ui(query, limit):
    if not query:
        return "⚠️ Kuch search karo!"
    try:
        data = _search(query, int(limit))
        if "error" in data:
            return f"❌ Error: {data['error']}"
        if not data.get("results"):
            return f"❌ No results for: **{query}**"
        
        out = f"🔍 **{query}** - {data['count']} results"
        if data.get("searched_in"):
            out += f" (searched in: {data['searched_in']})"
        out += "\n\n"
        
        for i, row in enumerate(data["results"], 1):
            fields = [f"{k}: {v}" for k, v in row.items() if v]
            out += f"**{i}.** " + ", ".join(fields[:5]) + "\n\n"
        return out
    except Exception as e:
        return f"❌ Error: {str(e)}"

demo = gr.Interface(
    fn=search_ui,
    inputs=[
        gr.Textbox(label="🔍 Search", placeholder="Phone, username, or name..."),
        gr.Slider(1, 50, value=10, step=1, label="Max Results")
    ],
    outputs=gr.Markdown(),
    title="📡 Telegram Search API",
    description="Search Telegram database | Built by @SOCIALBANNERR"
)

app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
