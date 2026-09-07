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
HF_DATASET = "sauravsingh2111/Tgdata"
HF_FILE = "TELEGRAM_MASTER_DB.parquet"
REMOTE_URL = f"https://huggingface.co/datasets/{HF_DATASET}/resolve/main/{HF_FILE}"

# Environment config
PARALLELISM = int(os.environ.get("TG_PARALLEL", "2"))
THREADS_PER_CONN = int(os.environ.get("TG_THREADS_PER_CONN", "2"))
DUPLICATE_CAP = 2

# Searchable fields (adjust based on actual columns)
SEARCH_FIELDS = [
    "phoneNumber", "username", "name", "userId",
    "bio", "country", "city", "lastSeen"
]
NUMBER_FIELDS = ["phoneNumber", "userId"]

# ── DuckDB Connection Pool ──────────────────────────────────────────────────
_conns: list[duckdb.DuckDBPyConnection] = []
_conns_lock = threading.Lock()
_thread_local = threading.local()
pool = ThreadPoolExecutor(max_workers=PARALLELISM, thread_name_prefix="duck")


def _new_conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    # Maya Render fix: set home & extension dir to /tmp
    con.execute("SET home_directory='/tmp'")
    con.execute("SET extension_directory='/tmp/duckdb_extensions'")
    con.execute("INSTALL parquet; LOAD parquet;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET threads = {THREADS_PER_CONN}")
    
    # Directly read from remote URL (NO DOWNLOAD!)
    con.execute(f"""
        CREATE OR REPLACE VIEW tg_data AS 
        SELECT * FROM read_parquet('{REMOTE_URL}')
    """)
    return con


def _thread_id() -> int:
    tid = getattr(_thread_local, "id", None)
    if tid is None:
        with _conns_lock:
            tid = len(_conns)
            _thread_local.id = tid
    return tid


def _get_conn() -> duckdb.DuckDBPyConnection:
    ident = _thread_id()
    with _conns_lock:
        while len(_conns) <= ident:
            _conns.append(_new_conn())
    return _conns[ident]


# ── Search Logic ────────────────────────────────────────────────────────────
def _run_search(field: str, value: str, mode: str, limit: int) -> dict:
    if field not in SEARCH_FIELDS:
        raise ValueError(f"Unknown field: {field}")
    
    v = value.replace("'", "''")
    limit_with_buffer = limit * DUPLICATE_CAP + 20
    
    if mode == "exact":
        sql = f"SELECT * FROM tg_data WHERE {field} = '{v}' LIMIT {limit_with_buffer}"
    elif mode == "contains":
        v2 = v.replace("%", r"\%").replace("_", r"\_")
        sql = f"SELECT * FROM tg_data WHERE {field} ILIKE '%{v2}%' ESCAPE '\\' LIMIT {limit_with_buffer}"
    else:
        raise ValueError(f"Unknown mode: {mode}")

    con = _get_conn()
    rows = con.execute(sql).fetchall()
    cols = [d[0] for d in con.description]
    
    results = []
    for r in rows:
        record = dict(zip(cols, r))
        results.append(record)
    
    return {
        "field": field,
        "value": value,
        "mode": mode,
        "count": len(results),
        "results": results[:limit]
    }


def _unified_search(q: str, limit: int = 10) -> dict:
    q = q.strip()
    if not q:
        return {"query": q, "searched_fields": [], "count": 0, "results": []}
    
    all_results = []
    searched = []
    
    # Try phone first, then username, then name
    if q.isdigit() and len(q) >= 8:
        r = _run_search("phoneNumber", q, "exact", limit)
        if r["results"]:
            all_results.extend(r["results"])
            searched.append("phoneNumber")
    
    if not all_results:
        r = _run_search("username", q, "contains", limit)
        if r["results"]:
            all_results.extend(r["results"])
            searched.append("username")
    
    if not all_results:
        r = _run_search("name", q, "contains", limit)
        if r["results"]:
            all_results.extend(r["results"])
            searched.append("name")
    
    return {
        "query": q,
        "searched_fields": searched,
        "count": len(all_results),
        "results": all_results[:limit]
    }


# ── FastAPI App ─────────────────────────────────────────────────────────────
fastapi_app = FastAPI(
    title="Telegram Database Search API",
    description="🚀 Built by @SOCIALBANNERR | Channel: @modxpatel | Data: sauravsingh2111/Tgdata",
    version="1.0.0"
)


class BatchRequest(BaseModel):
    queries: list[dict[str, Any]]
    limit: int = 10


@fastapi_app.get("/")
def root():
    return {
        "app": "Telegram Database Search API",
        "dataset": HF_DATASET,
        "file": HF_FILE,
        "size": "~7.94 GB (streamed, not downloaded)",
        "indexes": {"phone": True, "username": True, "name": True},
        "columns": SEARCH_FIELDS,
        "docs": "/docs",
        "developer": "@SOCIALBANNERR",
        "channel": "@modxpatel",
        "deployed_on": "Maya Render",
        "note": "Data is streamed remotely, no download required"
    }


@fastapi_app.get("/health")
def health():
    return {
        "status": "ok",
        "dataset": HF_DATASET,
        "streaming": True,
        "developer": "@SOCIALBANNERR"
    }


@fastapi_app.get("/search")
async def search(
    q: str | None = Query(None),
    field: str | None = Query(None),
    mode: str = Query("exact"),
    limit: int = Query(10, ge=1, le=100),
    pretty: bool = Query(True),
):
    q_val = (q or "").strip()
    if not q_val:
        raise HTTPException(422, "Provide 'q' parameter")
    
    loop = asyncio.get_running_loop()
    if field:
        data = await loop.run_in_executor(pool, _run_search, field, q_val, mode, limit)
    else:
        data = await loop.run_in_executor(pool, _unified_search, q_val, limit)
    
    result = {
        "success": bool(data["count"]),
        **data,
        "total": data["count"],
        "developer": "@SOCIALBANNERR",
        "channel": "@modxpatel"
    }
    content = json.dumps(result, indent=2 if pretty else None, ensure_ascii=False)
    return Response(content=content, media_type="application/json")


@fastapi_app.post("/search/parallel")
async def search_parallel(req: BatchRequest):
    if not req.queries:
        raise HTTPException(400, "queries must not be empty")
    if len(req.queries) > 50:
        raise HTTPException(400, "max 50 queries per batch")
    
    loop = asyncio.get_running_loop()
    tasks = [
        loop.run_in_executor(pool, _run_search,
                             item.get("field", "phoneNumber"),
                             item.get("value", ""),
                             item.get("mode", "exact"),
                             int(item.get("limit", req.limit)))
        for item in req.queries
    ]
    results = await asyncio.gather(*tasks)
    
    return Response(
        content=json.dumps({
            "searches": len(req.queries),
            "results": list(results),
            "developer": "@SOCIALBANNERR",
            "channel": "@modxpatel"
        }, indent=2, ensure_ascii=False),
        media_type="application/json"
    )


# ── Pinger ──────────────────────────────────────────────────────────────────
async def pinger():
    port = os.getenv("PORT", "7860")
    url = f"http://localhost:{port}/health"
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            await asyncio.sleep(120)
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    print(f"[Pinger] ✅ Keep-alive ping | Developer: @SOCIALBANNERR")
                else:
                    print(f"[Pinger] ⚠️ Status: {resp.status_code}")
            except Exception as e:
                print(f"[Pinger] ❌ Error: {e}")


@fastapi_app.on_event("startup")
async def startup_event():
    print("🚀 Starting Telegram Search API | Developer: @SOCIALBANNERR")
    asyncio.create_task(pinger())


# ── Gradio UI ───────────────────────────────────────────────────────────────
def format_result(row: dict) -> str:
    lines = []
    for field in SEARCH_FIELDS:
        val = row.get(field, "")
        if val:
            lines.append(f"**{field}:** {val}")
    return "\n\n".join(lines)


def search_ui(query: str, limit: int) -> str:
    if not query or not query.strip():
        return "⚠️ Kuch toh search karo — phone, username, ya name daalo."
    
    try:
        data = _unified_search(query.strip(), int(limit))
    except Exception as e:
        return f"❌ Error: {str(e)}"
    
    count = data["count"]
    results = data["results"]
    searched = ", ".join(data.get("searched_fields", []))
    
    if not results:
        return f"🔍 **Query:** `{query}`\n**Searched:** {searched}\n\n❌ **No data found**"
    
    header = f"🔍 **Query:** `{query}`  |  **Found:** {count} results  |  **Searched:** {searched}\n\n---\n\n"
    parts = []
    for i, row in enumerate(results, 1):
        parts.append(f"### Result {i}\n{format_result(row)}")
    return header + "\n\n---\n\n".join(parts)


def build_ui():
    with gr.Blocks(
        title="Telegram DB Search | @SOCIALBANNERR",
        theme=gr.themes.Soft(),
        css="""
        .main-title { text-align: center; margin-bottom: 0; color: #2563eb; }
        .footer { text-align: center; color: #888; margin-top: 20px; }
        .badge { background: linear-gradient(135deg, #2563eb, #7c3aed); color: white; padding: 4px 12px; border-radius: 20px; display: inline-block; }
        """
    ) as demo:
        gr.Markdown(
            """
            # 📡 Telegram Database Search API
            ## 🚀 Built by @SOCIALBANNERR | Channel: @modxpatel
            """,
            elem_classes="main-title"
        )
        gr.Markdown("Search **Telegram Master Database** (streamed remotely) — phone, username, name & more")
        
        with gr.Row():
            with gr.Column(scale=3):
                query_input = gr.Textbox(
                    label="Search Query",
                    placeholder="Phone number, username, ya name daalo...",
                    lines=1,
                )
            with gr.Column(scale=1):
                limit_slider = gr.Slider(
                    minimum=1, maximum=50, value=10, step=1,
                    label="Max Results",
                )
        
        search_btn = gr.Button("🔍 Search", variant="primary", size="lg")
        output = gr.Markdown(label="Results")
        
        search_btn.click(
            fn=search_ui,
            inputs=[query_input, limit_slider],
            outputs=output,
        )
        query_input.submit(
            fn=search_ui,
            inputs=[query_input, limit_slider],
            outputs=output,
        )
        
        gr.Markdown("---")
        with gr.Accordion("📡 API Info", open=False):
            gr.Markdown("""
**Endpoints:**
- `GET /search?q=<query>` — Search all fields
- `GET /search?field=phoneNumber&q=1234567890` — Specific field
- `GET /health` — Health check
- `GET /docs` — Swagger UI

**Source:** [sauravsingh2111/Tgdata](https://huggingface.co/datasets/sauravsingh2111/Tgdata)
            """)
        
        gr.Markdown(
            f"""
            <div class='footer'>
            <span class='badge'>👨‍💻 @SOCIALBANNERR</span>
            📢 Channel: <a href="https://t.me/modxpatel" target="_blank">@modxpatel</a>
            🚀 Hosted on <strong>Maya Render</strong>
            📦 Data streamed remotely (no download)
            </div>
            """,
            elem_classes="footer"
        )
    
    return demo


# ── Mount & Run ─────────────────────────────────────────────────────────────
demo = build_ui()
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
