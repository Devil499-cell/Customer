import asyncio
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import duckdb
import gradio as gr
import httpx
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel

# ── Config ──────────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))

# Remote Parquet URL (NO DOWNLOAD!)
REMOTE_URL = "https://huggingface.co/datasets/sauravsingh2111/Tgdata/resolve/main/TELEGRAM_MASTER_DB.parquet"

PARALLELISM = int(os.environ.get("TG_PARALLEL", "2"))
THREADS_PER_CONN = int(os.environ.get("TG_THREADS_PER_CONN", "2"))

SEARCH_FIELDS = ["phoneNumber", "username", "name", "userId", "bio", "country", "city"]

# ── DuckDB Connection ──────────────────────────────────────────────────────
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
    con.execute(f"CREATE OR REPLACE VIEW tg_data AS SELECT * FROM read_parquet('{REMOTE_URL}')")
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

# ── Search ─────────────────────────────────────────────────────────────────
def _search(field: str, value: str, mode: str, limit: int):
    if field not in SEARCH_FIELDS:
        return {"field": field, "value": value, "mode": mode, "count": 0, "results": []}
    
    v = value.replace("'", "''")
    if mode == "exact":
        sql = f"SELECT * FROM tg_data WHERE {field} = '{v}' LIMIT {limit + 10}"
    else:
        v2 = v.replace("%", r"\%").replace("_", r"\_")
        sql = f"SELECT * FROM tg_data WHERE {field} ILIKE '%{v2}%' ESCAPE '\\' LIMIT {limit + 10}"
    
    con = _get_conn()
    rows = con.execute(sql).fetchall()
    cols = [d[0] for d in con.description]
    results = [dict(zip(cols, r)) for r in rows][:limit]
    return {"field": field, "value": value, "mode": mode, "count": len(results), "results": results}

def _unified_search(q: str, limit: int = 10):
    q = q.strip()
    if not q:
        return {"query": q, "count": 0, "results": []}
    
    if q.isdigit() and len(q) >= 8:
        r = _search("phoneNumber", q, "exact", limit)
        if r["results"]:
            return {"query": q, "count": len(r["results"]), "results": r["results"]}
    
    r = _search("username", q, "contains", limit)
    if r["results"]:
        return {"query": q, "count": len(r["results"]), "results": r["results"]}
    
    r = _search("name", q, "contains", limit)
    return {"query": q, "count": len(r["results"]), "results": r["results"]}

# ── FastAPI ──────────────────────────────────────────────────────────────
fastapi_app = FastAPI(title="Telegram Search API")

@fastapi_app.get("/")
def root():
    return {"app": "Telegram Search API", "developer": "@SOCIALBANNERR", "channel": "@modxpatel"}

@fastapi_app.get("/health")
def health():
    return {"status": "ok"}

@fastapi_app.get("/search")
async def search(q: str = Query(...), limit: int = Query(10, ge=1, le=100)):
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(pool, _unified_search, q, limit)
    return Response(content=json.dumps(data, indent=2), media_type="application/json")

# ── Gradio UI ──────────────────────────────────────────────────────────────
def search_ui(query, limit):
    if not query:
        return "⚠️ Kuch search karo!"
    try:
        data = _unified_search(query, int(limit))
        if not data["results"]:
            return f"❌ No results for: {query}"
        out = f"🔍 **{query}** - {data['count']} results\n\n"
        for i, row in enumerate(data["results"][:10], 1):
            out += f"**{i}.** " + ", ".join(f"{k}: {v}" for k, v in row.items() if v) + "\n\n"
        return out
    except Exception as e:
        return f"❌ Error: {e}"

demo = gr.Interface(
    fn=search_ui,
    inputs=[gr.Textbox(label="Search"), gr.Slider(1, 50, value=10, label="Limit")],
    outputs=gr.Markdown(),
    title="Telegram Search API",
    description="Search phone, username, name by @SOCIALBANNERR"
)

app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 7860)))
