# tools/object_counter/vision.py

import base64
import json
from openai import OpenAI


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Zet afbeelding om naar base64-string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def build_prompt(object_description: str) -> str:
    """Vision prompt met duidelijke instructies."""
    return f"""
Je bent een AI vision model. Tel de individuele objecten in de afbeelding.

Object om te tellen: {object_description}

Regels:
- Elke fysiek gescheiden eenheid telt als 1 object.
- Gestapeld, naast elkaar of overlappend telt als meerdere objecten.
- Gebruik je beste visuele inschatting.
- Geef ALLEEN JSON terug zoals hieronder.

Return ONLY this JSON:
{{"count": <number>}}
"""


def count_objects_in_image(
    openai_client: OpenAI,
    image_bytes: bytes,
    image_mime: str,
    object_description: str,
) -> int:
    """
    Vision counting via OpenAI Responses API.
    """

    try:
        b64 = encode_image_to_base64(image_bytes)
        mime = image_mime or "image/jpeg"

        prompt = build_prompt(object_description)

        response = openai_client.responses.create(
            model="gpt-4.1",  # Vision-enabled model
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime};base64,{b64}"
                        }
                    ]
                }
            ],
            response_format={
                "type": "json_object"
            },
        )

        raw = response.output[0].content[0].text

    except Exception as e:
        print(f"❌ Vision API fout: {e}")
        return 0

    # JSON parsing
    try:
        data = json.loads(raw)
        count = int(data.get("count", 0))
        return max(0, count)
    except Exception:
        print("⚠️ Kon JSON niet parsen.")
        print("Raw output:", raw)
        return 0
