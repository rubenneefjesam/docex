# tools/object_counter/vision.py

import base64
import json
import streamlit as st
from groq import Groq


def encode_image_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def build_prompt(object_description: str) -> str:
    return f"""
You are an AI vision model. Count the INDIVIDUAL objects in the image.

Object to count: {object_description}

Rules:
- Each physically separate item counts as 1.
- Stacked, aligned, touching or overlapping items are still multiple items.
- Never treat a stack as a single object.
- Use your best visual estimate.

Return ONLY this JSON:
{{"count": <number>}}
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
