import json
import requests
from pathlib import Path
from groq import Groq

# ===== SWITCH HERE =====
BACKEND = "groq"           # "groq" for development, "ollama" for local testing

GROQ_MODEL   = "qwen/qwen3.8-27b"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_URL   = "http://localhost:11434/api/chat"

# path: core/llm.py → parent = core/ → parent = robocup_agent/
SECRETS_PATH = Path(__file__).resolve().parent.parent / "config" / "key.json"


def load_secret(name):
    with open(SECRETS_PATH, "r") as f:
        return json.load(f)[name]


groq_client = Groq(api_key=load_secret("GROQ_API_KEY")) if BACKEND == "groq" else None


def call_groq(messages):
    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        response_format={"type": "json_object"},  # force valid JSON
        reasoning_effort="none",                  # turn off Qwen3 "thinking" → faster, clean output
        temperature=0.3,                          # less random = more consistent actions
    )
    return completion.choices[0].message.content


def call_ollama(messages):
    response = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "messages": messages,
        "format": "json",
        "stream": False,
        "keep_alive": "30m",
    })
    response.raise_for_status()
    return response.json()["message"]["content"]


def call_llm(messages):
    """The rest of the project only ever calls this."""
    if BACKEND == "groq":
        return call_groq(messages)
    return call_ollama(messages)


def parse_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ---- test ----
if __name__ == "__main__":
    import time
    test_messages = [
        {"role": "system", "content":
            'You are a hospital guide robot. Reply ONLY with JSON like '
            '{"action": "speak", "text": "..."}'},
        {"role": "user", "content": "Hello, where is the X-ray room?"},
    ]

    print("BACKEND:", BACKEND)
    for i in range(3):
        start = time.time()
        raw = call_llm(test_messages)
        action = parse_json(raw)
        print(f"Call {i+1}: {time.time() - start:.2f} s → {action}")