"""Turn a short microphone recording into editable question text."""

MAX_AUDIO_BYTES = 2 * 1024 * 1024
AUDIO_FORMATS = {
    "audio/webm": "webm",
    "audio/mp4": "mp4",
    "audio/ogg": "ogg",
}

PROMPTS = {
    "zh": "將這段臺灣華語錄音轉寫為繁體中文。保留英文專有名詞。主題可能涉及東吳大學資料科學系、資工、資管、師資與實驗室。",
    "en": "Transcribe this recording in English. The topic is the Department of Data Science at Soochow University (SCU): courses, faculty, labs, admissions and careers.",
}


def transcribe(client, audio: bytes, media_type: str, lang: str = "zh") -> str:
    result = client.audio.transcriptions.create(
        model="gpt-transcribe",
        file=(f"question.{AUDIO_FORMATS[media_type]}", audio, media_type),
        prompt=PROMPTS.get(lang, PROMPTS["zh"]),
    )
    return result.text.strip()
