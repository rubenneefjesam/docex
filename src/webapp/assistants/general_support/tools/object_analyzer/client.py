# tools/object_counter/client.py

import os
from openai import OpenAI


def get_openai_client() -> OpenAI:
    """
    Haalt de OpenAI client op via Codespaces environment variables.
    Verwacht: OPENAI_KEY (en optioneel OPENAI_ORG_ID, OPENAI_PROJECT_ID)
    """

    api_key = os.getenv("OPENAI_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "❌ OPENAI_KEY is niet gevonden in de environment variables. "
            "Zorg dat je Codespaces secret 'OPENAI_KEY' hebt ingesteld."
        )

    # optioneel (alleen invullen als je deze gebruikt)
    org = os.getenv("OPENAI_ORG_ID", None)
    project = os.getenv("OPENAI_PROJECT_ID", None)

    try:
        return OpenAI(
            api_key=api_key,
            organization=org,
            project=project,
        )
    except Exception as e:
        raise RuntimeError(f"❌ Fout bij initialiseren van OpenAI-client: {e}")
