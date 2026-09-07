import asyncio
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import duckdb
import gradio as gr
import httpx
from fastapi import FastAPI, Query, Response

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
    con.execute(f"""
        CREATE OR REPLACE VIEW tg_data AS 
        SELECT * FROM read_parquet('{REMOTE_URL}')
    """)
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
    
    # Phone number exact match
    if q.isdigit() and len(q) >= 8:
        sql = f"SELECT * FROM tg_data WHERE phoneNumber = '{q}' LIMIT {limit + 5}"
        con = _get_conn()
        rows = con.execute(sql).fetchall()
        if rows:
            cols = [d[0] for d in con.description]
            results = [dict(zip(cols, r)) for r in rows][:limit]
            return {"query": q, "count": len(results), "results": results}
    
    # Username contains
    sql = f"SELECT * FROM tg_data WHERE username ILIKE '%{q}%' LIMIT {limit + 5}"
    con = _get_conn()
    rows = con.execute(sql).fetchall()
    if rows:
        cols = [d[0] for d in con.description]
        results = [dict(zip(cols, r)) for r in rows][:limit]
        return {"query": q, "count": len(results), "results": results}
    
    # Name contains
    sql = f"SELECT * FROM tg_data WHERE name ILIKE '%{q}%' LIMIT {limit + 5}"
    con = _get_conn()
    rows = con.execute(sql).fetchall()
    if rows:
        cols = [d[0] for d in con.description]
        results = [dict(zip(cols, r)) for r in rows][:limit]
        return {"query": q, "count": len(results), "results": results}
    
    return {"query": q, "count": 0, "results": []}

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
        "dataset": "sauravsingh2111/Tgdata"
    }

@fastapi_app.get("/health")
def health():
    return {"status": "ok", "developer": "@SOCIALBANNERR"}

@fastapi_app.get("/search")
async def search(q: str = Query(...), limit: int = Query(10, ge=1, le=100)):
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(pool, _search, q, limit)
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json"
    )

# ── Gradio UI ──────────────────────────────────────────────────────────
def search_ui(query, limit):
    if not query:
        return "⚠️ Kuch search karo!"
    try:
        data = _search(query, int(limit))
        if not data["results"]:
            return f"❌ No results for: **{query}**"
        
        out = f"🔍 **{query}** - {data['count']} results\n\n"
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
    description="Search 7.94 GB Telegram database | Built by @SOCIALBANNERR"
)

app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
