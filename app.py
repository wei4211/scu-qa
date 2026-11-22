"""Flask entry point for the department Q&A interface."""

import os
import re
import threading
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Request, jsonify, make_response, render_template, request

from assistant_service import DepartmentAssistant
from transcription import AUDIO_FORMATS, MAX_AUDIO_BYTES, transcribe
from ui_text import ERRORS, SCRIPT_TEXT, STAT_LABELS, TEXT, pick_lang, topics

PHOTO_DIR = Path(__file__).with_name("static") / "photos"
PHOTO_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
REEL_MIN_ITEMS = 8
MAX_HISTORY_TURNS = 3
MAX_HISTORY_ANSWER = 1000


class ChatRequest(Request):
    @property
    def max_content_length(self):
        if self.endpoint == "voice":
            return MAX_AUDIO_BYTES + 8192
        return super().max_content_length


def reel_photos() -> list[dict]:
    """Photos for the home-page reel: every image in static/photos, by file name.

    The alt text comes from the file name, so name files after what they show
    (e.g. 「專題成果展.jpg」); a leading number such as 「01_」 only sets the order
    and is left out of the alt text. The list repeats until it is long enough to loop
    without a gap; an empty list makes the page show placeholders.
    """
    if not PHOTO_DIR.is_dir():
        return []
    photos = [
        {"file": f"photos/{item.name}", "alt": re.sub(r"^\d+[_-]", "", item.stem).replace("_", " ").replace("-", " ")}
        for item in sorted(PHOTO_DIR.iterdir())
        if item.suffix.lower() in PHOTO_TYPES and not item.name.startswith(".")
    ]
    if not photos:
        return []
    return photos * -(-REEL_MIN_ITEMS // len(photos))


def home_stats(sources) -> dict[str, list[dict]]:
    """Department figures for the home page in each language, counted from the scraped site data."""
    teachers = {name for item in sources if item.page == "專任師資" for name in item.names}
    labs = {
        item.title for item in sources
        if item.page == "跨域實驗室" and not item.title.endswith(("實驗室介紹", "實驗室研究領域"))
    }
    projects = {item.title for item in sources if item.page == "學生專題影音"}
    credit_pages = sorted(
        (item for item in sources if item.page == "必選修科目表" and item.title.endswith("畢業學分")),
        key=lambda item: item.title,
    )
    credits = re.search(r"共計 (\d+)", credit_pages[-1].text) if credit_pages else None
    year = re.search(r"(\d{3})學年度", credit_pages[-1].title) if credit_pages else None
    values = {"teachers": len(teachers), "labs": len(labs), "projects": len(projects)}
    if credits:
        values["credits"] = int(credits.group(1))
    result = {}
    for lang, labels in STAT_LABELS.items():
        items = []
        for key, value in values.items():
            unit, label = labels[key]
            if key == "credits":
                label = label.format(year=year.group(1), ad=int(year.group(1)) + 1911) if year else label.split("（")[0].split(" (")[0]
            if value:
                items.append({"value": value, "unit": unit, "label": label})
        result[lang] = items
    return result


def request_lang() -> str:
    """The visitor's language: ?lang= on the page, the JSON body or form on the API, else the saved cookie."""
    body = request.get_json(silent=True) if request.is_json else None
    from_body = body.get("lang") if isinstance(body, dict) else None
    return pick_lang(request.args.get("lang") or from_body or request.form.get("lang") or request.cookies.get("lang"))


def create_app(assistant=None):
    app = Flask(__name__)
    app.request_class = ChatRequest
    app.config["MAX_CONTENT_LENGTH"] = 32768
    if assistant is None:
        load_dotenv(Path(__file__).with_name(".env"), interpolate=False)
        key = os.getenv("OPENAI_API_KEY")
        if key:
            from openai import OpenAI

            assistant = DepartmentAssistant(OpenAI(api_key=key, timeout=20, max_retries=2))
            # Load the vector index in the background so the first visitor does not wait for it.
            threading.Thread(target=assistant.index.warm_up, daemon=True).start()
        else:
            assistant = DepartmentAssistant()

    stats = home_stats(assistant.sources)

    @app.get("/")
    def home():
        lang = request_lang()
        page = make_response(render_template(
            "index.html", preview=assistant.index is None, photos=reel_photos(), stats=stats[lang],
            lang=lang, t=TEXT[lang], js_text=SCRIPT_TEXT[lang], topics=topics(lang),
        ))
        if request.args.get("lang"):
            page.set_cookie("lang", lang, max_age=365 * 24 * 3600, samesite="Lax")
        return page

    @app.post("/api/ask")
    def ask():
        data = request.get_json(silent=True)
        errors = ERRORS[request_lang()]
        question = data.get("question") if isinstance(data, dict) else None
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 400:
            return jsonify(error=errors["question_length"]), 400
        history = data.get("history", [])
        if not isinstance(history, list) or len(history) > MAX_HISTORY_TURNS:
            return jsonify(error=errors["history_format"]), 400
        for turn in history:
            if (
                not isinstance(turn, dict)
                or not isinstance(turn.get("question"), str)
                or not isinstance(turn.get("answer"), str)
                or not 1 <= len(turn["question"].strip()) <= 400
                or not 1 <= len(turn["answer"].strip()) <= MAX_HISTORY_ANSWER
            ):
                return jsonify(error=errors["history_format"]), 400
        try:
            context = [{"question": turn["question"], "answer": turn["answer"]} for turn in history]
            return jsonify(assistant.answer(question.strip(), context, request_lang()))
        except Exception as error:
            app.logger.warning("Question processing failed (%s)", type(error).__name__)
            return jsonify(error=errors["answer_failed"]), 503

    @app.post("/api/transcribe")
    def voice():
        lang = request_lang()
        errors = ERRORS[lang]
        if assistant.client is None:
            return jsonify(error=errors["voice_disabled"]), 503
        upload = request.files.get("audio")
        if upload is None or upload.mimetype not in AUDIO_FORMATS:
            return jsonify(error=errors["audio_unreadable"]), 400
        audio = upload.read(MAX_AUDIO_BYTES + 1)
        if len(audio) > MAX_AUDIO_BYTES:
            return jsonify(error=errors["audio_too_large"]), 413
        if not audio:
            return jsonify(error=errors["audio_empty"]), 400
        try:
            transcript = transcribe(assistant.client, audio, upload.mimetype, lang)
        except Exception as error:
            app.logger.warning("Transcription failed (%s)", type(error).__name__)
            return jsonify(error=errors["transcribe_failed"]), 503
        if not transcript:
            return jsonify(error=errors["transcript_empty"]), 422
        return jsonify(text=transcript)

    @app.errorhandler(413)
    def request_too_large(_error):
        errors = ERRORS[pick_lang(request.cookies.get("lang"))]
        if request.endpoint == "voice":
            return jsonify(error=errors["audio_too_large"]), 413
        return jsonify(error=errors["question_too_large"]), 413

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=int(os.getenv("PORT", "5001")))
