import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
from google import genai

ROOT = Path(__file__).resolve().parents[1]  # repo root
load_dotenv(dotenv_path=ROOT / ".env")

STATE_PATH = ROOT / "jobs" / "job_0001" / "state" / "state.json"
SCHEMA_PATH = ROOT / "state" / "state_schema.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_json(path: Path, obj: dict) -> None:
    save_text(path, json.dumps(obj, ensure_ascii=False, indent=2))


def validate_state(state: dict) -> None:
    schema = load_json(SCHEMA_PATH)
    Draft202012Validator(schema).validate(state)


def extract_first_json_object(text: str) -> dict:
    """
    Gemini иногда оборачивает JSON в текст. Мы выдёргиваем первый JSON-объект.
    Если JSON чистый — тоже сработает.
    """
    text = text.strip()
    # Попытка 1: целиком JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Попытка 2: вытащить первую {...} структуру
    # Это грубо, но на MVP ок. Дальше можно ужесточать.
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output.")
    return json.loads(match.group(0))


def build_message(prompt_text: str, state: dict) -> str:
    # Промпт уже задаёт формат. Мы просто прикладываем state как вход.
    return (
        prompt_text.strip()
        + "\n\nINPUT STATE (JSON):\n"
        + json.dumps(state, ensure_ascii=False)
    )


def call_gemini(model: str, message: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("No API key found. Set GEMINI_API_KEY (preferred) or GOOGLE_API_KEY in .env or env vars.")

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(model=model, contents=message)
    return resp.text or ""


def main():
    pass_id = os.getenv("PASS_ID", "pass_1_decide")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    prompt_path = ROOT / "passes" / pass_id / "prompt.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")

    state = load_json(STATE_PATH)
    validate_state(state)

    prompt_text = prompt_path.read_text(encoding="utf-8")
    message = build_message(prompt_text, state)

    raw = call_gemini(model=model, message=message)

    out_dir = ROOT / "jobs" / state["meta"]["job_id"] / "output"
    save_text(out_dir / f"{pass_id}__raw.txt", raw)

    parsed = extract_first_json_object(raw)
    save_json(out_dir / f"{pass_id}__out.json", parsed)

    print(f"OK: {pass_id} output saved to jobs/{state['meta']['job_id']}/output")


if __name__ == "__main__":
    main()
