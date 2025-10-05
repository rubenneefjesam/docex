import os
import sys
from typing import Optional

# optional SDKs
try:
    from groq import Groq
except Exception:
    Groq = None

try:
    import openai
except Exception:
    openai = None


def get_groq_client() -> Optional[Groq]:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key or Groq is None:
        return None
    try:
        return Groq(api_key=key)
    except Exception as e:
        print(f"[llm_utils] Groq client init failed: {e}", file=sys.stderr)
        return None


def call_llm_system_prompt(prompt: str, system: str, groq_client: Optional[Groq] = None) -> str:
    # Try Groq chat first
    if groq_client and Groq is not None:
        try:
            resp = groq_client.chat.completions.create(
                model=os.environ.get("GROQ_CHAT_MODEL", "llama-3.1-8b-instant"),
                temperature=float(os.environ.get("GROQ_TEMPERATURE", "0.2")),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            err = f"[Groq error] {e}"
            print(err, file=sys.stderr)
            return err

    # Fallback to OpenAI chat
    if openai is not None and os.environ.get("OPENAI_API_KEY"):
        try:
            openai.api_key = os.environ.get("OPENAI_API_KEY")
            model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.2")),
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as e:
            err = f"[OpenAI error] {e}"
            print(err, file=sys.stderr)
            return err

    return "[No LLM configured: set GROQ_API_KEY or OPENAI_API_KEY]"


# Backwards-compatible aliases (soms andere modules verwachten underscore-namen)
_get_groq_client = get_groq_client
_call_llm_system_prompt = call_llm_system_prompt
