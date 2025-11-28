# tools/object_counter/vision.py

import base64
import json
import streamlit as st
from groq import Groq


def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def build_prompt(object_description: str) -> str:
    """
    Bouwt de telling-prompt, inclusief speciale regels voor hekpanelen.
    """
    obj = object_description.lower()
    extra_rules = ""

    if "hek" in obj or "fence" in obj:
        extra_rules = """
Specific rules for construction fence panels:
- Count EACH INDIVIDUAL fence panel.
- A fence panel stored sideways has ONE large vertical tube visible.
- Count the number of vertical tubes = number of panels.
- A stack is NOT 1 object.
"""

    prompt = f"""
You are an expert AI VISION model that counts INDIVIDUAL construction objects.

Object to count: {object_description}

General rules:
- Count each physically separate object as ONE.
- If objects are stacked, aligned or touching: still count individually.
- A stack is NOT one object.
- Return your best estimate.

{extra_rules}

Output format:
ONLY return JSON:
{{"count": <number_of_objects>}}
"""
    return prompt


def count_objects_in_image(
    groq_client: Groq,
    image_bytes: bytes,
    image_mime: str,
    object_description: str,
) -> int:
    """
    Vision-telling via het Groq Scout model.
    """

    image_b64 = encode_image_to_base64(image_bytes)
    mime = image_mime or "image/jpeg"
    data_url = f"data:{mime};base64,{image_b64}"

    prompt = build_prompt(object_description)

    try:
        completion = groq_client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )

    except Exception as e:
        st.error(f"❌ Vision API fout: {e}")
        return 0

    raw = completion.choices[0].message.content

    # JSON parsen
    try:
        data = json.loads(raw)
        count = int(data.get("count", 0))
        return max(0, count)
    except Exception:
        st.warning("⚠️ Kon JSON niet parsen.")
        st.text(f"Raw output:\n{raw}")
        return 0
