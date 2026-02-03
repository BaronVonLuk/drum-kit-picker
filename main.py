import os
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from kits import pick_top_kits, DrumKit


DO_INFERENCE_BASE_URL = "https://inference.do-ai.run/v1"  # DigitalOcean serverless inference base URL :contentReference[oaicite:1]{index=1}


app = FastAPI(title="Drum Kit Picker")
templates = Jinja2Templates(directory=".")


def env_required(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


async def do_chat(model: str, api_key: str, messages: list[dict]) -> str:
    url = "https://inference.do-ai.run/v1/responses"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": messages[0]["content"],
            },
            {
                "role": "user",
                "content": messages[1]["content"],
            },
        ],
        "temperature": 0.4,
        "max_output_tokens": 500,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    return data["output"][0]["content"][0]["text"]



@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    # Simple inline HTML so you don't need separate template files.
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>Drum Kit Picker</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; max-width: 760px; }
      label { display:block; margin-top: 1rem; font-weight: 600; }
      select, input { width: 100%; padding: .6rem; margin-top: .4rem; }
      button { margin-top: 1.2rem; padding: .8rem 1rem; width: 100%; font-weight: 700; }
      .hint { color: #444; font-size: .92rem; }
    </style>
  </head>
  <body>
    <h1>Pick a Drum Kit</h1>
    <p class="hint">Answer a few questions. You’ll get 2–3 recommendations and why they fit.</p>

    <form action="/recommend" method="post">
      <label>Kit type</label>
      <select name="kit_type" required>
        <option value="electronic">Electronic</option>
        <option value="acoustic">Acoustic</option>
      </select>

      <label>Budget (USD)</label>
      <input name="budget" type="number" min="200" max="10000" step="50" value="900" required/>

      <label>Space</label>
      <select name="space" required>
        <option value="apartment">Apartment</option>
        <option value="house">House</option>
        <option value="studio">Studio / rehearsal</option>
      </select>

      <label>Skill level</label>
      <select name="skill" required>
        <option value="beginner">Beginner</option>
        <option value="intermediate">Intermediate</option>
        <option value="advanced">Advanced</option>
      </select>

      <label>Main genre</label>
      <select name="genre" required>
        <option value="rock">Rock</option>
        <option value="metal">Metal</option>
        <option value="pop">Pop</option>
        <option value="funk">Funk</option>
        <option value="jazz">Jazz</option>
        <option value="hiphop">Hip-hop</option>
        <option value="edm">EDM</option>
        <option value="country">Country</option>
      </select>

      <label>Quiet practice is a priority</label>
      <select name="quiet_priority" required>
        <option value="yes">Yes</option>
        <option value="no">No</option>
      </select>

      <button type="submit">Recommend</button>
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

    # 1) Deterministic shortlisting (keeps the LLM from hallucinating random models).
    top = pick_top_kits(prefs, k=3)

    # 2) LLM writes the explanation and the final output.
    model_access_key = env_required("DO_MODEL_ACCESS_KEY")
    model_id = os.getenv("DO_MODEL_ID", "llama3.3-70b-instruct")  # example model id from DO docs :contentReference[oaicite:2]{index=2}

    shortlist_text = "\n".join(
        [
            f"- {k.name} | {k.kit_type} | ${k.price_min}-${k.price_max} | space:{k.space} | skill:{k.skill} | notes:{k.notes}"
            for k in top
        ]
    )

    system = (
        "You recommend drum kits. "
        "Use ONLY the provided shortlist as the candidate kits. "
        "Be direct. Point out conflicts (ex: acoustic in an apartment). "
        "Return a clean, readable result with sections: Best pick, Runner-up, Third option, What to buy, Setup tips."
    )

    user = (
        f"User preferences:\n"
        f"- type: {prefs['kit_type']}\n"
        f"- budget: ${prefs['budget']}\n"
        f"- space: {prefs['space']}\n"
        f"- skill: {prefs['skill']}\n"
        f"- genre: {prefs['genre']}\n"
        f"- quiet priority: {prefs['quiet_priority']}\n\n"
        f"Shortlist (only options you may recommend):\n{shortlist_text}"
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
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; max-width: 860px; }}
      pre {{ white-space: pre-wrap; background: #f6f6f6; padding: 1rem; border-radius: 12px; }}
      a {{ display:inline-block; margin-top: 1rem; }}
    </style>
  </head>
  <body>
    <h1>Your recommendations</h1>
    <pre>{rec}</pre>
    <a href="/">← Back</a>
  </body>
</html>
"""
