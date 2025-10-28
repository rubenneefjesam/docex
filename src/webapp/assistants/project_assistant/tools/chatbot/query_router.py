# chatbot/query_router.py
"""
QueryRouter: brug tussen natuurlijke taalvragen en je onderliggende data + indices.

Taken:
- Parse intent van vraag (project-, klant- of documentgericht)
- Zoek juiste indexen via index_utils
- Embed de vraag en voer retrieval uit
- Samenvat resultaten met llm_utils

Auteur: Ruben & ChatGPT (GPT-5)
"""

import re
from typing import List, Dict, Optional
from pathlib import Path

from . import index_utils, embed_utils, llm_utils


class QueryRouter:
    """
    Centrale orchestrator voor het afhandelen van gebruikersvragen.

    Voorbeeldgebruik:
    -----------------
        from chatbot.query_router import QueryRouter
        from chatbot.embed_utils import Embedder
        from chatbot.llm_utils import get_groq_client

        router = QueryRouter(Embedder(), get_groq_client())
        answer = router.route_query("Wanneer start de bouw van het project van Van Dijk?")
        print(answer)
    """

    def __init__(self, embedder: embed_utils.Embedder, llm_client=None):
        self.embedder = embedder
        self.llm_client = llm_client

    # ---------------------------
    # 1. Intent Parsing
    # ---------------------------
    def parse_intent(self, question: str) -> Dict[str, Optional[str]]:
        """
        Probeer te bepalen of de vraag klantgericht, projectgericht of documentgericht is.

        Returns:
            {
              "intent": "project" | "client" | "document" | "unknown",
              "client_id": Optional[str],
              "project_id": Optional[str],
              "doc_type": Optional[str]
            }
        """
        q = question.lower()
        result = {"intent": "unknown", "client_id": None, "project_id": None, "doc_type": None}

        # detecteer klant ID's of namen (C001, klantnaam)
        cid_match = re.search(r"\b(c\d{3,6})\b", q)
        if cid_match:
            result["client_id"] = cid_match.group(1).upper()
            result["intent"] = "client"

        # detecteer project ID's (P1001)
        pid_match = re.search(r"\b(p\d{3,6})\b", q)
        if pid_match:
            result["project_id"] = pid_match.group(1).upper()
            result["intent"] = "project"

        # detecteer type document
        if any(kw in q for kw in ["technische omschrijving", "orderbevestiging", "klantcommunicatie"]):
            result["doc_type"] = next(
                (kw for kw in ["technische omschrijving", "orderbevestiging", "klantcommunicatie"] if kw in q),
                None,
            )
            result["intent"] = "document"

        # fallback heuristiek
        if "project" in q and result["intent"] == "unknown":
            result["intent"] = "project"
        elif "klant" in q and result["intent"] == "unknown":
            result["intent"] = "client"

        return result

    # ---------------------------
    # 2. Retrieval
    # ---------------------------
    def retrieve_context(self, question: str, intent_info: Dict[str, Optional[str]], top_k: int = 5) -> List[Dict]:
        """
        Embed de vraag en zoek relevante tekstfragmenten in de juiste index(en).
        """
        q_emb = self.embedder.embed([question])[0]

        client_id = intent_info.get("client_id")
        project_id = intent_info.get("project_id")

        # Als specifieke client/project bekend is
        if client_id and project_id and index_utils.index_exists(client_id, project_id):
            return index_utils.retrieve(client_id, project_id, q_emb, top_k=top_k)

        # Anders: zoek in alle beschikbare indexen (optioneel)
        results = []
        index_dir = index_utils.INDEX_DIR
        for path in index_dir.glob("index_*.jsonl"):
            # haal ID's uit bestandsnaam
            m = re.search(r"INDEX_(C\d+)_?(P\d+)?", path.name.upper())
            if not m:
                continue
            c, p = m.group(1), m.group(2)
            try:
                subset = index_utils.retrieve(c, p, q_emb, top_k=2)
                results.extend(subset)
            except Exception:
                continue

        # sorteer op score
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results[:top_k]

    # ---------------------------
    # 3. Samenvatting / Antwoord
    # ---------------------------
    def summarize(self, question: str, retrieved: List[Dict]) -> str:
        """
        Bouw een compacte samenvatting van de gevonden resultaten via LLM.
        """
        if not retrieved:
            return "Ik heb geen relevante informatie kunnen vinden in de documenten."

        # combineer tekstvelden
        context_texts = "\n\n".join(r.get("text", "")[:1500] for r in retrieved if "text" in r)
        system_prompt = (
            "Je bent een behulpzame assistent die vragen over bouwprojecten, klanten en documenten beantwoordt.\n"
            "Gebruik de gegeven context om een duidelijk, feitelijk antwoord te formuleren.\n"
            "Wees beknopt, maar volledig genoeg om de essentie over te brengen.\n"
        )
        user_prompt = f"Vraag: {question}\n\nContext:\n{context_texts}"

        return llm_utils.call_llm_system_prompt(user_prompt, system_prompt, groq_client=self.llm_client)

    # ---------------------------
    # 4. Route de volledige query
    # ---------------------------
    def route_query(self, question: str, top_k: int = 5) -> str:
        """
        Volledige pipeline:
        - parse intent
        - retrieve context
        - genereer antwoord
        """
        intent_info = self.parse_intent(question)
        retrieved = self.retrieve_context(question, intent_info, top_k=top_k)
        answer = self.summarize(question, retrieved)
        return answer


# Snelle test (CLI)
if __name__ == "__main__":
    from .embed_utils import Embedder
    from .llm_utils import get_groq_client

    router = QueryRouter(Embedder(), get_groq_client())
    vraag = "Wat staat er in de technische omschrijving van klant C005 over zonnepanelen?"
    print(router.route_query(vraag))
