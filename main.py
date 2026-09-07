import json
import os
import httpx
from fastapi import FastAPI, Query, Response
import gradio as gr

app = FastAPI(title="Telegram Search API (HF Proxy)")

# Hugging Face Datasets Server API
HF_API = "https://datasets-server.huggingface.co/rows"
DATASET = "sauravsingh2111/Tgdata"

def search_hf(q: str, limit: int = 10):
    """Search using Hugging Face API"""
    # Step 1: Get total rows count
    try:
        # Search in all rows (filtering later)
        offset = 0
        results = []
        
        while len(results) < limit and offset < 1000:  # Max 1000 rows scan
            resp = httpx.get(
                HF_API,
                params={
                    "dataset": DATASET,
                    "config": "default",
                    "split": "train",
                    "offset": offset,
                    "length": 100
                },
                timeout=30
            )
            if resp.status_code != 200:
                break
                
            data = resp.json()
            rows = data.get("rows", [])
            if not rows:
                break
                
            # Filter rows matching query
            for row in rows:
                row_data = row.get("row", {})
                # Search in user_id, username, first_name, phone
                search_str = json.dumps(row_data).lower()
                if q.lower() in search_str:
                    results.append(row_data)
                    if len(results) >= limit:
                        break
            
            offset += 100
            if data.get("partial", False):
                break
                
        return {
            "query": q,
            "count": len(results),
            "results": results[:limit],
            "source": "Hugging Face API"
        }
    except Exception as e:
        return {"query": q, "count": 0, "results": [], "error": str(e)}

@app.get("/")
def root():
    return {
        "app": "Telegram Search API (HF Proxy)",
        "developer": "@SOCIALBANNERR",
        "channel": "@modxpatel",
        "dataset": DATASET,
        "method": "Hugging Face Datasets Server API",
        "status": "active"
    }

@app.get("/health")
def health():
    return {"status": "ok", "api": "HF Proxy", "developer": "@SOCIALBANNERR"}

@app.get("/search")
async def search(q: str = Query(...), limit: int = Query(10, ge=1, le=100)):
    data = search_hf(q, limit)
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json"
    )

def search_ui(query, limit):
    if not query:
        return "⚠️ Kuch search karo!"
    data = search_hf(query, int(limit))
    if "error" in data:
        return f"❌ Error: {data['error']}"
    if not data.get("results"):
        return f"❌ No results for: **{query}**"
    
    out = f"🔍 **{query}** - {data['count']} results\n\n"
    for i, row in enumerate(data["results"], 1):
        fields = [f"{k}: {v}" for k, v in row.items() if v]
        out += f"**{i}.** " + ", ".join(fields[:5]) + "\n\n"
    return out

demo = gr.Interface(
    fn=search_ui,
    inputs=[
        gr.Textbox(label="🔍 Search", placeholder="User ID, username, or name..."),
        gr.Slider(1, 50, value=10, step=1, label="Max Results")
    ],
    outputs=gr.Markdown(),
    title="📡 Telegram Search API (HF Proxy)",
    description="Search via Hugging Face API | Built by @SOCIALBANNERR"
)

app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
