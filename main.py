import os
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

from kits import pick_top_kits, DrumKit

DO_INFERENCE_BASE_URL = "https://inference.do-ai.run"

app = FastAPI(title="Drum Kit Picker")


def env_required(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


async def do_chat(model: str, api_key: str, messages: List[Dict[str, Any]]) -> str:
    url = f"{DO_INFERENCE_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 500,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    return data["choices"][0]["message"]["content"]


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Drum Kit Picker</title>
</head>
<body>
  <h1>Drum Kit Picker</h1>

  <form action="/recommend" method="post">

    <label>Kit Type</label><br/>
    <select name="kit_type" required>
      <option value="acoustic">Acoustic</option>
      <option value="electronic">Electronic</option>
    </select><br/><br/>

    <label>Budget (USD)</label><br/>
    <input type="number" name="budget" value="1000" required/><br/><br/>

    <label>Space</label><br/>
    <select name="space" required>
      <option value="apartment">Apartment</option>
      <option value="house">House</option>
      <option value="studio">Studio / Practice Space</option>
    </select><br/><br/>

    <label>Skill</label><br/>
    <select name="skill" required>
      <option value="beginner">Beginner</option>
      <option value="intermediate">Intermediate</option>
      <option value="advanced">Advanced</option>
    </select><br/><br/>

    <label>Genre</label><br/>
    <select name="genre" required>
      <option value="rock">Rock</option>
      <option value="metal">Metal</option>
      <option value="jazz">Jazz</option>
      <option value="funk">Funk</option>
      <option value="pop">Pop</option>
    </select><br/><br/>

    <label>Quiet Priority</label><br/>
    <select name="quiet_priority" required>
      <option value="yes">Yes</option>
      <option value="no">No</option>
    </select><br/><br/>

    <button type="submit">Get recommendation</button>

  </form>
</body>
</html>
"""


@app.post("/recommend", response_class=HTMLResponse)
async def recommend(
    kit_type: str = Form(...),
    budget: int = Form(...),
    space: str = Form(...),
    skill: str = Form(...),
    genre: str = Form(...),
    quiet_priority: str = Form(...),
) -> str:
    prefs = {
        "kit_type": kit_type,
        "budget": int(budget),
        "space": space,
        "skill": skill,
        "genre": genre,
        "quiet_priority": quiet_priority == "yes",
    }

    # Deterministic shortlist
    top = pick_top_kits(prefs, k=3)

    model_access_key = env_required("DO_MODEL_ACCESS_KEY")
    model_id = os.getenv("DO_MODEL_ID", "llama3.3-70b-instruct")

    shortlist_text = "\n".join(
        [
            f"- {k.name} | {k.kit_type} | ${k.price_min}-${k.price_max} | "
            f"space:{k.space} | skill:{k.skill} | notes:{k.notes}"
            for k in top
        ]
    )

    system = (
        "You recommend drum kits. "
        "Use ONLY the provided shortlist. "
        "Be direct and practical. "
        "Return sections: Best pick, Runner-up, Third option, What to buy, Setup tips."
    )

    user = (
        f"User preferences:\n"
        f"- type: {prefs['kit_type']}\n"
        f"- budget: ${prefs['budget']}\n"
        f"- space: {prefs['space']}\n"
        f"- skill: {prefs['skill']}\n"
        f"- genre: {prefs['genre']}\n"
        f"- quiet priority: {prefs['quiet_priority']}\n\n"
        f"Shortlist:\n{shortlist_text}"
    )

    try:
        rec = await do_chat(
            model=model_id,
            api_key=model_access_key,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except Exception as e:
        rec = f"AI call failed: {type(e).__name__}: {e}"

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Recommendations</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      margin: 2rem;
      max-width: 860px;
    }}
    pre {{
      white-space: pre-wrap;
      background: #f6f6f6;
      padding: 1rem;
      border-radius: 12px;
    }}
    a {{
      display: inline-block;
      margin-top: 1rem;
    }}
  </style>
</head>
<body>
  <h1>Your recommendations</h1>
  <pre>{rec}</pre>
  <a href="/">← Back</a>
</body>
</html>
"""
