# src/webapp/assistants/project_assistant/tools/chatbot/search_index.py
"""
Zoekfunctie voor de chatbot-index.
Gebruik:
    python -m src.webapp.assistants.project_assistant.tools.chatbot.search_index \
        --query "zoekterm"
"""

import argparse
from pathlib import Path
from .embed_utils import Embedder, retrieve

def search(query: str, client_id: str = "LOCAL", project_id: str = "INDEX", top_k: int = 5):
    """Zoekt in de bestaande index op basis van een query-tekst."""
    embedder = Embedder()
    q_emb = embedder.embed_texts([query])[0]  # embedding van de zoekterm
    results = retrieve(client_id, project_id, q_emb, top_k=top_k)

    if not results:
        print("❌ Geen resultaten gevonden.")
        return

    print(f"\n🔎 Resultaten voor query: '{query}'\n")
    for i, r in enumerate(results, start=1):
        print(f"{i}. 📄 {Path(r['source']).name}")
        print(f"   🧩 Score: {r['_score']:.4f}")
        print(f"   🧠 Chunk-ID: {r['chunk_id']}  ({r['total_chunks']} total)")
        print(f"   🗂️  Bestand: {r['source']}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zoek in de chatbot-index op basis van tekstquery.")
    parser.add_argument("--query", type=str, required=True, help="Tekstuele zoekterm of vraag.")
    parser.add_argument("--top-k", type=int, default=5, help="Aantal resultaten om te tonen.")
    args = parser.parse_args()

    search(args.query, top_k=args.top_k)
