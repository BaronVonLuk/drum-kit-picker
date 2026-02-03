import os
import asyncio
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

# ---------- Environment helpers ----------
def env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Environment variable {name} is required")
    return value

# ---------- FastAPI setup ----------
app = FastAPI()
templates = Jinja2Templates(directory="templates")  # ensure you have a 'templates' folder

# ---------- AI Call ----------
async def do_chat(model: str, api_key: str, messages: list[dict]) -> str:
    """
    Calls DigitalOcean Serverless Inference API.
    """
    url = "https://inference.do-ai.run/v1/responses"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "input": messages,
        "max_output_tokens": 500,
        "temperature": 0.4,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    return data["output"][0]["content"][0]["text"]

# ---------- Dummy drum kits for demo ----------
class DrumKit:
    def __init__(self, name, kit_type, price_min, price_max, space, skill, notes):
        self.name = name
        self.kit_type = kit_type
        self.price_min = price_min
        self.price_max = price_max
        self.space = space
        self.skill = skill
        self.notes = notes

kits_db = [
    DrumKit("Yamaha Stage Custom", "acoustic", 700, 900, "medium", "intermediate", "classic kit"),
    DrumKit("Roland V-Drums TD-17", "electronic", 1200, 1500, "small", "beginner", "great for apartments"),
    DrumKit("Pearl Export", "acoustic", 600, 800, "medium", "beginner", "reliable starter kit"),
]

def pick_top_kits(prefs: dict, k=3):
    # Simple filter demo
    filtered = [kit for kit in kits_db if kit.kit_type == prefs.get("kit_type", kit.kit_type)]
    return filtered[:k]

# ---------- Routes ----------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/recommend", response_class=HTMLResponse)
async def recommend(
    request: Request,
    kit_type: str = Form(...),
    budget: str = Form(...),
    space: str = Form(...),
    skill: str = Form(...),
    genre: str = Form(...),
    quiet_priority: str = Form(...)
):
    # Step 1: prepare user prefs
    prefs = {
        "kit_type": kit_type,
        "budget": int(budget),
        "space": space,
        "skill": skill,
        "genre": genre,
        "quiet_priority": quiet_priority.lower() == "yes",
    }

    # Step 2: pick top kits
    top = pick_top_kits(prefs, k=3)

    # Step 3: format shortlist
    shortlist_text = "\n".join(
        [
            f"- {k.name} | {k.kit_type} | ${k.price_min}-${k.price_max} | space:{k.space} | skill:{k.skill} | notes:{k.notes}"
            for k in top
        ]
    )

    # Step 4: call AI for a final recommendation
    system = "You are a professional drum tech. Recommend a drum kit based on user preferences."
    user_message = f"User preferences:\n{prefs}\nTop options:\n{shortlist_text}"

    model_id = env_required("DO_MODEL_ID")
    model_access_key = env_required("DO_MODEL_ACCESS_KEY")

    try:
        rec_text = await do_chat(
            model=model_id,
            api_key=model_access_key,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
        )
    except Exception as e:
        rec_text = f"AI call failed: {e}"
