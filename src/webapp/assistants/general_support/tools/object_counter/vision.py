# tools/object_counter/vision.py

import base64
import json
from openai import OpenAI


# ----------------------------
# Helper: Base64 converter
# ----------------------------
def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# ----------------------------
# 1) Automatische beeldbeschrijving
# ----------------------------
def describe_image(openai_client: OpenAI, image_bytes: bytes, image_mime: str) -> str:
    """
    Laat OpenAI beschrijven wat het model visueel detecteert.
    Volledig generiek — geen aannames over objecttypes.
    """

    b64 = encode_image_to_base64(image_bytes)
    mime = image_mime or "image/jpeg"

    response = openai_client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Geef een zeer korte, duidelijke beschrijving van wat je visueel ziet "
                            "op deze afbeelding. Benoem de relevante objecten en hun context. "
                            "Wees precies maar niet langer dan 1–2 zinnen."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime};base64,{b64}",
                    },
                ],
            }
        ],
    )

    return response.output[0].content[0].text.strip()


# ----------------------------
# 2) Object-counting functie
# ----------------------------
def count_objects_in_image(
    openai_client: OpenAI,
    image_bytes: bytes,
    image_mime: str,
    object_description: str,
) -> int:
    """
    Tel het aantal individuele objecten in een afbeelding.
    Volledig generiek — de gebruiker bepaalt welk object geteld wordt.
    """

    if not image_bytes:
        return 0

    b64 = encode_image_to_base64(image_bytes)
    mime = image_mime or "image/jpeg"

    prompt = f"""
Je bent een AI Vision model.
Tel het aantal INDIVIDUELE objecten in de afbeelding die overeenkomen met:

Object: "{object_description}"

Regels:
- Tel elke VISUEEL afzonderlijke eenheid als 1 object.
- Objecten mogen overlappen, gestapeld zijn of gedeeltelijk zichtbaar zijn: tel elk individueel stuk.
- Maak geen aannames: gebruik alleen zichtbare kenmerken.
- Gebruik je beste visuele schatting.
- Retourneer ALLEEN geldige JSON in dit formaat:
{{"count": <integer>}}
"""

    response = openai_client.responses.create(
        model="gpt-4.1",
        response_format={"type": "json_object"},
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime};base64,{b64}",
                    },
                ],
            }
        ],
    )

    raw = response.output[0].content[0].text

    try:
        data = json.loads(raw)
        count = int(data.get("count", 0))
        return max(0, count)
    except Exception:
        print("⚠️ Kon JSON niet parsen. Ruwe output:")
        print(raw)
        return 0
