# tools/object_counter/vision.py

import base64
import json
from openai import OpenAI


# ----------------------------
# Base64 helper
# ----------------------------
def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# ----------------------------
# 1) AUTOMATISCHE BESCHRIJVING
# ----------------------------
def describe_image(openai_client: OpenAI, image_bytes: bytes, image_mime: str) -> str:
    """
    Geeft een compacte beschrijving van wat het Vision-model ziet.
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
                            "Beschrijf heel kort wat je visueel ziet op deze afbeelding. "
                            "Maximaal 1-2 zinnen. Wees concreet en beschrijvend."
                        )
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime};base64,{b64}"
                    }
                ]
            }
        ]
    )

    return response.output[0].content[0].text.strip()


# ----------------------------
# 2) OBJECTEN TELLEN
# ----------------------------
def count_objects_in_image(
    openai_client: OpenAI,
    image_bytes: bytes,
    image_mime: str,
    object_description: str,
) -> int:
    """
    Vision-based counting, generiek.
    """

    if not image_bytes:
        return 0

    b64 = encode_image_to_base64(image_bytes)
    mime = image_mime or "image/jpeg"

    prompt = f"""
Je bent een AI Vision model. Tel het aantal INDIVIDUELE objecten in de afbeelding dat overeenkomt met:

Object: "{object_description}"

Regels:
- Tel elke afzonderlijke visueel herkenbare eenheid als 1 object.
- Objecten mogen overlappen, gestapeld zijn of deels zichtbaar zijn.
- Gebruik uitsluitend zichtbare kenmerken.
- Retourneer STRICT JSON in dit formaat:
{{"count": <integer>}}
"""

    response = openai_client.responses.create(
        model="gpt-4.1",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime};base64,{b64}"
                    }
                ]
            }
        ]
    )

    raw = response.output[0].content[0].text.strip()

    # JSON parsing
    try:
        data = json.loads(raw)
        return int(data.get("count", 0))
    except Exception:
        print("⚠️ Vision output was geen JSON:")
        print(raw)
        return 0
