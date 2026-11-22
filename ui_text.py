"""Interface wording for the two supported languages (Traditional Chinese and English).

The page template, the browser scripts and the API error messages all read from here,
so adding or changing a phrase only needs an edit in this file.
"""

LANGS = ("zh", "en")
DEFAULT_LANG = "zh"

TEXT = {
    "zh": {
        "html_lang": "zh-Hant-TW",
        "page_title": "東吳大學資料科學系智慧問答系統",
        "brand": "東吳大學",
        "brand_strong": "資料科學系",
        "nav_label": "系上網站與社群",
        "new_window": "（另開新視窗）",
        "site_link": "系所網站",
        "lang_label": "切換語言",
        "reel_label": "東吳資科活動照片",
        "photo": "照片",
        "ai_tag": "AI 示意圖",
        "title_small": "東吳大學資料科學系",
        "title_big": "智慧問答系統",
        "greeting": "嗨嗨～歡迎來到東吳資科！👋 我是你的資科小助理。好奇資料科學到底在學什麼、畢業後能做什麼，或學長姐做過哪些有趣的專題嗎？儘管問我吧！",
        "preview_note": "目前顯示搜尋到的系網段落。",
        "messages_label": "對話紀錄",
        "question_label": "輸入問題",
        "placeholder": "輸入你想了解的問題…",
        "voice_start": "開始語音輸入",
        "voice_title": "語音輸入",
        "send": "送出問題",
        "topics_label": "快速認識資科：點選主題直接提問",
        "stats_title": "用數據認識東吳資科",
        "home_note": "回答依東吳大學資料科學系官網公開資料整理，正式資訊請以系網公告為準。",
        "bubble_left": ["嗨！我是資科小助理", "資料會說話 📊", "Python・統計・AI"],
        "bubble_right": ["有問題儘管問我！", "想認識資科嗎？", "點下面的卡片試試 👇"],
    },
    "en": {
        "html_lang": "en",
        "page_title": "SCU Data Science Smart Q&A",
        "brand": "Soochow University",
        "brand_strong": "Data Science",
        "nav_label": "Department website and social media",
        "new_window": " (opens in a new window)",
        "site_link": "Department site",
        "lang_label": "Change language",
        "reel_label": "Photos of SCU Data Science",
        "photo": "Photo",
        "ai_tag": "AI illustration",
        "title_small": "SCU Department of Data Science",
        "title_big": "Smart Q&A",
        "greeting": "Hi, welcome to SCU Data Science! 👋 I'm your department assistant. Curious what you'll learn, where graduates work, or what students build? Just ask!",
        "preview_note": "Showing matching passages from the department website.",
        "messages_label": "Conversation",
        "question_label": "Your question",
        "placeholder": "Ask about the department…",
        "voice_start": "Start voice input",
        "voice_title": "Voice input",
        "send": "Send question",
        "topics_label": "Quick start: pick a topic to ask about it",
        "stats_title": "SCU Data Science in numbers",
        "home_note": "Answers are based on the SCU Data Science website. Please check official announcements for details.",
        "bubble_left": ["Hi! I'm your DS assistant", "Data tells stories 📊", "Python · Stats · AI"],
        "bubble_right": ["Ask me anything!", "Curious about Data Science?", "Try a card below 👇"],
    },
}

# Topic cards under the question box: (question sent, card title, short description, colour hue, icon).
_ICONS = {
    "code": '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>',
    "lab": '<path d="M9.5 3.5h5M10.5 3.5v5.2L5.6 17a2.3 2.3 0 0 0 2 3.5h8.8a2.3 2.3 0 0 0 2-3.5l-4.9-8.3V3.5"/><path d="M7.6 14h8.8"/>',
    "career": '<rect x="3.5" y="7.5" width="17" height="12" rx="2.5"/><path d="M8.8 7.5V5.8c0-.9.7-1.6 1.6-1.6h3.2c.9 0 1.6.7 1.6 1.6v1.7M3.5 12.5h17"/>',
}
TOPICS = {
    "zh": [
        ("資科系在學什麼？", "資科系在學什麼", "程式設計、統計分析、AI 與產業應用，一次看懂", 232, "code"),
        ("有哪些實驗室？", "跨域實驗室", "NLP、多媒體情感運算、醫療大數據…", 262, "lab"),
        ("畢業後可以做什麼工作？", "畢業出路", "資料科學家、數據分析師、金融科技…", 202, "career"),
    ],
    "en": [
        ("What does the Department of Data Science teach?", "What you'll learn", "Coding, statistics, AI and its uses", 232, "code"),
        ("What research labs does the department have?", "Research labs", "NLP, multimedia, medical data…", 262, "lab"),
        ("What jobs can graduates get?", "Career paths", "Data scientist, analyst, fintech…", 202, "career"),
    ],
}


def topics(lang: str) -> list[dict]:
    return [
        {"question": q, "title": t, "desc": d, "tone": h, "icon": _ICONS[i]}
        for q, t, d, h, i in TOPICS[lang]
    ]


# Labels for the department figures; the numbers themselves are counted from the site data.
STAT_LABELS = {
    "zh": {
        "teachers": ("位", "專任師資"),
        "labs": ("間", "跨域實驗室"),
        "projects": ("件", "系網收錄專題作品"),
        "credits": ("學分", "畢業學分（{year} 學年度入學）"),
    },
    "en": {
        "teachers": ("", "Full-time faculty"),
        "labs": ("", "Research labs"),
        "projects": ("", "Student projects"),
        "credits": ("credits", "To graduate ({ad} entry)"),
    },
}

# Strings the browser scripts show (chat and voice input).
SCRIPT_TEXT = {
    "zh": {
        "lang": "zh",
        "you": "你",
        "assistant": "東吳資科助理",
        "searching": "正在查找系網資料…",
        "still_searching": "還在查找資料，請稍候…",
        "sources": "資料來源",
        "follow_ups": "可以接著問",
        "offline": "目前無法連線，請稍後再試。",
        "voice_stop": "停止錄音並轉成文字",
        "voice_start": "開始語音輸入",
        "voice_disabled": "語音輸入尚未啟用。",
        "voice_unsupported": "此瀏覽器目前無法錄音，請用文字輸入。",
        "voice_empty": "沒有收到錄音，請再試一次。",
        "voice_transcribing": "正在轉成文字…",
        "voice_truncated": "已填入前 400 字，請確認後送出。",
        "voice_filled": "已填入辨識文字，可以修改後再送出。",
        "voice_failed": "語音轉文字失敗，請再試一次。",
        "voice_waiting": "等候麥克風權限。錄音將由 OpenAI 轉成文字。",
        "voice_interrupted": "錄音中斷，請再試一次。",
        "voice_recording": "錄音中，再按一下交由 OpenAI 轉成文字。",
        "voice_denied": "未取得麥克風權限，請允許後再試。",
        "voice_no_mic": "無法開啟麥克風，請確認裝置後再試。",
        "seconds": "秒",
    },
    "en": {
        "lang": "en",
        "you": "You",
        "assistant": "SCU DS Assistant",
        "searching": "Searching the department website…",
        "still_searching": "Still looking, one moment…",
        "sources": "Sources",
        "follow_ups": "You could ask next",
        "offline": "Can't connect right now. Please try again later.",
        "voice_stop": "Stop recording and transcribe",
        "voice_start": "Start voice input",
        "voice_disabled": "Voice input is not enabled.",
        "voice_unsupported": "This browser can't record audio. Please type your question.",
        "voice_empty": "No recording was received. Please try again.",
        "voice_transcribing": "Transcribing…",
        "voice_truncated": "The first 400 characters were filled in. Please check before sending.",
        "voice_filled": "Transcript filled in. You can edit it before sending.",
        "voice_failed": "Transcription failed. Please try again.",
        "voice_waiting": "Waiting for microphone access. OpenAI will transcribe the recording.",
        "voice_interrupted": "Recording was interrupted. Please try again.",
        "voice_recording": "Recording. Tap again to transcribe with OpenAI.",
        "voice_denied": "Microphone access was denied. Please allow it and try again.",
        "voice_no_mic": "Can't open the microphone. Please check your device.",
        "seconds": "s",
    },
}

# Error messages returned by the API.
ERRORS = {
    "zh": {
        "question_length": "請輸入 1 至 400 字的問題。",
        "history_format": "對話內容格式有誤，請重新整理後再試。",
        "answer_failed": "目前無法產生回答，請稍後再試。",
        "voice_disabled": "語音輸入尚未啟用，請使用文字輸入。",
        "audio_unreadable": "無法讀取這段錄音，請再試一次。",
        "audio_too_large": "錄音檔太大，請縮短錄音。",
        "audio_empty": "沒有收到錄音，請再試一次。",
        "transcribe_failed": "語音轉文字失敗，請再試一次或改用文字輸入。",
        "transcript_empty": "這段錄音沒有辨識到文字，請再試一次。",
        "question_too_large": "問題太長，請縮短後再送出。",
    },
    "en": {
        "question_length": "Please enter a question of 1 to 400 characters.",
        "history_format": "The conversation data looks wrong. Please refresh the page and try again.",
        "answer_failed": "Can't generate an answer right now. Please try again later.",
        "voice_disabled": "Voice input is not enabled. Please type your question.",
        "audio_unreadable": "Couldn't read this recording. Please try again.",
        "audio_too_large": "The recording is too long. Please keep it shorter.",
        "audio_empty": "No recording was received. Please try again.",
        "transcribe_failed": "Transcription failed. Please try again or type your question.",
        "transcript_empty": "No speech was recognised in this recording. Please try again.",
        "question_too_large": "The question is too long. Please shorten it.",
    },
}


def pick_lang(value) -> str:
    return value if value in LANGS else DEFAULT_LANG
