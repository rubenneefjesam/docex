# === FILE: llm_utils.py ===
key = os.environ.get("GROQ_API_KEY", "").strip()
if not key:
return None
if Groq is None:
return None
try:
return Groq(api_key=key)
except Exception:
return None




def call_llm_system_prompt(prompt: str, system: str, groq_client: Optional[Groq] = None) -> str:
if groq_client and Groq is not None:
try:
resp = groq_client.chat.completions.create(
model=os.environ.get("GROQ_CHAT_MODEL", "llama-3.1-8b-instant"),
temperature=0.2,
messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
)
return resp.choices[0].message.content or ""
except Exception as e:
return f"[Groq error] {e}"


if openai is not None and os.environ.get("OPENAI_API_KEY"):
try:
openai.api_key = os.environ.get("OPENAI_API_KEY")
model = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
resp = openai.ChatCompletion.create(
model=model,
messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
temperature=0.2,
)
return resp["choices"][0]["message"]["content"]
except Exception as e:
return f"[OpenAI error] {e}"


return ""

