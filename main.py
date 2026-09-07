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

# Telegram dataset parts (54 parts, each with data_0.parquet)
HF_BASE = "https://huggingface.co/datasets/sauravsingh2111/Tgdata/resolve/main/TG_DATA_PARTS"
REMOTE_PARTS = [f"{HF_BASE}/part_id={i}/data_0.parquet" for i in range(54)]

PARALLELISM = int(os.environ.get("TG_PARALLEL", "2"))
THREADS_PER_CONN = int(os.environ.get("TG_THREADS_PER_CONN", "2"))
DUPLICATE_CAP = 2

# Search fields (based on actual Telegram data)
SEARCH_FIELDS = [
    "user_id",
    "username",
    "first_name",
    "last_name",
    "phone",
    "bio",
    "country",
    "city",
]
NUMBER_FIELDS = ["user_id", "phone"]

# ── DuckDB Connection Pool ──────────────────────────────────────────────────
_conns: list[duckdb.DuckDBPyConnection] = []
_conns_lock = threading.Lock()
_thread_local = threading.local()
pool = ThreadPoolExecutor(max_workers=PARALLELISM, thread_name_prefix="duck")


def _new_conn() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    # Maya Render fix
    con.execute("SET home_directory='/tmp'")
    con.execute("SET extension_directory='/tmp/duckdb_extensions'")
    con.execute("INSTALL parquet; LOAD parquet;")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    
    # Read all parts (ICMR style!)
    part_list = ", ".join([f"'{url}'" for url in REMOTE_PARTS])
    con.execute(f"""
        CREATE OR REPLACE VIEW tg_data AS 
        SELECT * FROM read_parquet([{part_list}])
    """)
    con.execute(f"SET threads = {THREADS_PER_CONN}")
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


# ── Dedup & Connected Records ───────────────────────────────────────────────
def _person_key(row: dict) -> tuple:
    uid = str(row.get("user_id") or "").strip()
    ph = str(row.get("phone") or "").strip()
    if uid or ph:
        return (uid, ph)
    return (row.get("username") or "").strip(), (row.get("first_name") or "").strip()


def _connected_numbers(row: dict) -> list[dict]:
    connected, seen = [], set()
    for field in NUMBER_FIELDS:
        raw = row.get(field)
        if raw is None:
            continue
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        connected.append({"field": field, "value": value})
    return connected


def _cap_duplicates(rows: list[dict]) -> list[dict]:
    seen: dict[tuple, int] = {}
    out = []
    for r in rows:
        k = _person_key(r)
        n = seen.get(k, 0)
        if n < DUPLICATE_CAP:
            seen[k] = n + 1
            record = dict(r)
            record["connected_numbers"] = _connected_numbers(record)
            out.append(record)
    return out


# ── Search Logic ────────────────────────────────────────────────────────────
def _run_field_search(field: str, value: str, mode: str, limit: int) -> dict:
    if field not in SEARCH_FIELDS:
        raise ValueError(f"Unknown field: {field}")
    v = value.replace("'", "''")

    if mode == "exact":
        if field == "user_id":
            sql = f"SELECT * FROM tg_data WHERE user_id = {v} LIMIT {limit * DUPLICATE_CAP + 20}"
        elif field == "phone":
            sql = f"SELECT * FROM tg_data WHERE phone = '{v}' LIMIT {limit * DUPLICATE_CAP + 20}"
        else:
            return {"field": field, "value": value, "mode": mode, "count": 0, "results": []}
    elif mode == "contains":
        v2 = v.replace("%", r"\%").replace("_", r"\_")
        sql = f"SELECT * FROM tg_data WHERE {field} ILIKE '%{v2}%' ESCAPE '\\' LIMIT {limit * DUPLICATE_CAP + 20}"
    else:
        raise ValueError(f"Unknown mode: {mode}")

    con = _get_conn()
    rows = con.execute(sql).fetchall()
    cols = [d[0] for d in con.description]
    results = _cap_duplicates([dict(zip(cols, r)) for r in rows])[:limit]
    return {"field": field, "value": value, "mode": mode, "count": len(results), "results": results}


def _unified_search(q: str, limit: int = 10) -> dict:
    q = q.strip()
    is_num = q.isdigit() and len(q) >= 8

    if is_num:
        all_rows = []
        searched = []
        
        # Search by user_id (primary key, integer)
        r = _run_field_search("user_id", q, "exact", limit)
        all_rows.extend(r["results"])
        searched.append("user_id")
        
        # If no results, try phone
        if not all_rows:
            r = _run_field_search("phone", q, "exact", limit)
            all_rows.extend(r["results"])
            searched.append("phone")
        
        all_rows = _cap_duplicates(all_rows)[:limit]
        return {
            "query": q, "searched_fields": searched,
            "count": len(all_rows), "results": all_rows,
        }
    else:
        # Text search: username, first_name, last_name
        all_rows = []
        searched = []
        
        # Try username
        r = _run_field_search("username", q, "contains", limit)
        all_rows.extend(r["results"])
        searched.append("username")
        
        # Try first_name
        if not all_rows:
            r = _run_field_search("first_name", q, "contains", limit)
            all_rows.extend(r["results"])
            searched.append("first_name")
        
        # Try last_name
        if not all_rows:
            r = _run_field_search("last_name", q, "contains", limit)
            all_rows.extend(r["results"])
            searched.append("last_name")
        
        all_rows = _cap_duplicates(all_rows)[:limit]
        return {
            "query": q, "searched_fields": searched,
            "count": len(all_rows), "results": all_rows,
        }


# ── FastAPI ──────────────────────────────────────────────────────────────────
fastapi_app = FastAPI(title="Telegram Search API")


class BatchRequest(BaseModel):
    queries: list[dict[str, Any]]
    limit: int = 10


@fastapi_app.get("/")
def root():
    return {
        "app": "Telegram Search API",
        "records": "4.9 GB (54 parts)",
        "indexes": {"user_id": True, "username": True, "phone": True},
        "columns": SEARCH_FIELDS,
        "docs": "/docs",
        "developer": "@SOCIALBANNERR | channel @modxpatel",
    }


@fastapi_app.get("/health")
def health():
    return {
        "status": "ok",
        "parts": len(REMOTE_PARTS),
        "developer": "@SOCIALBANNERR"
    }


@fastapi_app.get("/search")
async def search(
    q: str | None = Query(None),
    field: str | None = Query(None),
    mode: str = Query("exact"),
    limit: int = Query(10, ge=1, le=1000),
    pretty: bool = Query(True),
):
    q_val = (q or "").strip()
    if not q_val:
        raise HTTPException(422, "Provide q")
    loop = asyncio.get_running_loop()
    if field:
        data = await loop.run_in_executor(pool, _run_field_search, field, q_val, mode, limit)
    else:
        data = await loop.run_in_executor(pool, _unified_search, q_val, limit)
    result = {"success": bool(data["count"]), **data, "total": data["count"]}
    content = json.dumps(result, indent=2 if pretty else None, ensure_ascii=False)
    return Response(content=content, media_type="application/json")


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
                    print(f"[Pinger] OK")
                else:
                    print(f"[Pinger] Unexpected status: {resp.status_code}")
            except Exception as e:
                print(f"[Pinger] Error: {e}")


@fastapi_app.on_event("startup")
async def startup_event():
    asyncio.create_task(pinger())


# ── Gradio UI ───────────────────────────────────────────────────────────────
def format_result(row: dict) -> str:
    lines = []
    for field in SEARCH_FIELDS:
        val = row.get(field, "")
        if val:
            lines.append(f"**{field}:** {val}")
    cn = row.get("connected_numbers", [])
    if cn:
        nums = ", ".join(f"{c['field']}={c['value']}" for c in cn)
        lines.append(f"**connected:** {nums}")
    return "\n\n".join(lines)


def search_ui(query: str, limit: int) -> str:
    if not query or not query.strip():
        return "⚠️ Kuch toh search karo — user_id, username, ya phone daalo."

    q = query.strip()
    try:
        data = _unified_search(q, int(limit))
    except Exception as e:
        return f"❌ Error: {str(e)}"

    count = data["count"]
    results = data["results"]
    searched = ", ".join(data.get("searched_fields", []))

    if not results:
        return f"🔍 **Query:** `{q}`\n**Searched:** {searched}\n\n❌ **No data found**"

    header = f"🔍 **Query:** `{q}`  |  **Found:** {count} results  |  **Searched:** {searched}\n\n---\n\n"
    parts = []
    for i, row in enumerate(results, 1):
        parts.append(f"### Result {i}\n{format_result(row)}")
    return header + "\n\n---\n\n".join(parts)


def build_ui():
    with gr.Blocks(
        title="Telegram Search API",
        theme=gr.themes.Soft(),
        css="""
        .main-title { text-align: center; margin-bottom: 0; }
        .subtitle { text-align: center; color: #666; margin-top: 0; }
        .footer { text-align: center; color: #888; margin-top: 20px; }
        """
    ) as demo:
        gr.Markdown("# 📡 Telegram Search API", elem_classes="main-title")
        gr.Markdown("Search **4.9 GB Telegram database** — user_id, username, phone & more", elem_classes="subtitle")

        with gr.Row():
            with gr.Column(scale=3):
                query_input = gr.Textbox(
                    label="Search Query",
                    placeholder="User ID, username, ya phone daalo...",
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
**Endpoints** (via FastAPI):
- `GET /search?q=<user_id>` — Search by user ID
- `GET /search?q=<username>` — Search by username
- `GET /search?q=<phone>` — Search by phone
- `GET /health` — Health check
- `GET /docs` — Swagger UI

**Source:** [HF Dataset](https://huggingface.co/datasets/sauravsingh2111/Tgdata)
            """)

        gr.Markdown(
            "---\n"
            "<div class='footer'>"
            "👨‍💻 **Developer:** @SOCIALBANNERR  |  📢 **Channel:** @modxpatel"
            "</div>",
            elem_classes="footer"
        )

    return demo


demo = build_ui()
app = gr.mount_gradio_app(fastapi_app, demo, path="/")
