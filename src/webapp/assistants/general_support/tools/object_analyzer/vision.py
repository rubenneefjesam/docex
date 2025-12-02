# tools/object_analyzer/vision.py

import base64
import json
from openai import OpenAI
from .status_definitions import STATUS_DEFINITIONS


# ----------------------------
# Base64 helper
# ----------------------------
def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


# ----------------------------
# 1) OBJECT ANALYSE
# ----------------------------
def analyze_image(openai_client: OpenAI, image_bytes: bytes, image_mime: str) -> dict:
    """
    Herkent:
    - objectnaam (kort)
    - confidence (%)
    - status (gekozen uit vaste lijst)
    - status toelichting
    """

    b64 = encode_image_to_base64(image_bytes)
    mime = image_mime or "image/jpeg"

    # Maak een nette lijst voor de AI (alleen labels)
    status_labels = [v["label"] for v in STATUS_DEFINITIONS.values()]

    prompt = f"""
Je bent een AI Vision-inspectiemodel. Analyseer de afbeelding en geef ALLEEN terug in JSON.

Taak:
1. Herken het object in de afbeelding in maximaal 1–3 woorden.
2. Geef een confidence percentage: hoe zeker ben je dat dit het object is?
3. Bepaal de status van het object. Kies *uitsluitend* één van deze statussen:
   {status_labels}
4. Geef een korte status-toelichting (exact 1 zin), passend bij de gekozen status.

Regels:
- Maak de objectnaam kort en concreet, geen zinnetjes.
- Confidence is een integer (0–100).
- Toelichting moet nuttig, duidelijk en visueel afleidbaar zijn.
- Retourneer STRIKT geldige JSON:

{{
  "object": "<1-3 woorden>",
  "confidence": <integer>,
  "status": "<één van de statussen hierboven>",
  "status_description": "<1 zin>"
}}
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
        return {
            "object": data.get("object", "").strip(),
            "confidence": int(data.get("confidence", 0)),
            "status": data.get("status", "").strip(),
            "status_description": data.get("status_description", "").strip()
        }
    except Exception:
        print("⚠️ Vision output was geen valide JSON:")
        print(raw)
        return {
            "object": "onbekend",
            "confidence": 0,
            "status": "Onherkenbaar",
            "status_description": "De afbeelding is onvoldoende duidelijk om een status te bepalen."
        }


# ----------------------------
# 2) OBJECTEN TELLEN (onveranderd maar opgeschoond)
# ----------------------------
def count_objects_in_image(
    openai_client: OpenAI,
    image_bytes: bytes,
    image_mime: str,
    object_description: str,
) -> int:

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
- Retourneer STRICT JSON:
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

    try:
        data = json.loads(raw)
        return int(data.get("count", 0))
    except Exception:
        print("⚠️ Vision output was geen JSON:")
        print(raw)
        return 0
