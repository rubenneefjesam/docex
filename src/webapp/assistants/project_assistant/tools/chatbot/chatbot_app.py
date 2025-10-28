from pathlib import Path
from typing import Any
from fastapi import FastAPI, Form, HTTPException
from pydantic import BaseModel

from .index_utils import build_index
from .embed_utils import index_exists, retrieve
from .utils import metadata_exists
from .ui import run as ui_run

app = FastAPI(title="Client/Project Chatbot")


class ValidateResponse(BaseModel):
    exists: bool
    indexed: bool
    found_chunks: int


class IndexResponse(BaseModel):
    success: bool
    indexed_chunks: int


@app.post("/index", response_model=IndexResponse)
async def index_route(
    client_id: str = Form(...),
    project_id: str = Form(...)
) -> IndexResponse:
    """
    Indexeer alle documenten voor een given client/project.
    """
    if not metadata_exists(client_id, project_id):
        raise HTTPException(status_code=404, detail="Client/Project niet gevonden")

    try:
        chunk_count = build_index(client_id, project_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexeren mislukt: {e}")

    return IndexResponse(success=True, indexed_chunks=chunk_count)


@app.post("/validate", response_model=ValidateResponse)
async def validate_route(
    client_id: str = Form(...),
    project_id: str = Form(...)
) -> ValidateResponse:
    """
    Controleer of client/project bestaat en of er een index is.
    """
    exists = metadata_exists(client_id, project_id)
    indexed = exists and index_exists(client_id, project_id)
    found = 0

    if indexed:
        # retrieve met lege embedding geeft aantal beschikbare chunks
        sample = retrieve(client_id, project_id, q_emb=[], top_k=0)
        found = len(sample)

    return ValidateResponse(exists=exists, indexed=indexed, found_chunks=found)


@app.get("/run-ui")
async def run_ui() -> Any:
    """Expose UI entrypoint via HTTP voor local development."""
    return ui_run()


@app.post("/query")
async def query_route(
    client_id: str = Form(...),
    project_id: str = Form(...),
    question: str = Form(...)
):
    """
    Embedding van de vraag, retrieval en doorsturen naar LLM.
    Vervang '...' door je eigen embed-logica.
    """
    q_emb = ...  # embed vraag hier
    results = retrieve(client_id, project_id, q_emb)
    return {"answers": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
