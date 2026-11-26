"""Retrieve passages from the saved SCU pages."""

import re
from hashlib import sha256
from pathlib import Path
from threading import Lock

from sources import Source

EMBEDDING_MODEL = "text-embedding-3-small"
INDEX_DIR = Path(__file__).resolve().parent / ".chroma"
# "List all labs / teachers" needs every passage of that page, not just the top vector hits.
LIST_WORDS = ("哪些", "有誰", "哪幾", "列出", "所有", "全部", "名單", "幾位", "幾個")
GENERIC_TRIGRAMS = {"資料科", "料科學", "學年度", "必修科", "選修科", "修科目", "哪些課", "的課程"}
COURSE_YEAR = re.compile(r"(\d{3})學年度入學")
COURSE_PROGRAM = re.compile(r"(學士班|碩士班|碩士在職專班)｜\d{3}學年度入學")
TEACH_VERB = re.compile(r"教授(?=哪些|什麼|課|內容|的課)")
# Topic words, as patterns: 「教授哪些課程」 uses 教授 as "to teach", so it does not ask for the list of professors.
LIST_PAGES = {
    "跨域實驗室": re.compile(r"實驗室"),
    "專任師資": re.compile(r"老師|師資|教授"),
    "競賽成果": re.compile(r"競賽|比賽|得獎"),
}


def terms(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    for run in re.findall(r"[\u3400-\u9fff]+", text):
        words.extend(run[i:i + 2] for i in range(len(run) - 1))
    return set(words)


def trigrams(text: str) -> set[str]:
    grams = {word for word in re.findall(r"[a-z]{2,}", text.lower())}
    for run in re.findall(r"[\u3400-\u9fff]+", text):
        grams.update(run[i:i + 3] for i in range(len(run) - 2))
    return grams - GENERIC_TRIGRAMS


def course_matches(question: str, candidates, limit: int = 3) -> list[Source]:
    """Course-table passages listing a course whose name shares 3+ characters with the question."""
    query = trigrams(question)
    scored = []
    for item in candidates:
        if not COURSE_YEAR.search(item.title):
            continue
        courses = [line.split("｜", 1)[0] for line in item.text.split("\n")[1:]]
        hits = sum(1 for name in courses if query & trigrams(name))
        if hits:
            scored.append((hits, item))
    scored.sort(key=lambda match: match[0], reverse=True)
    return [item for _, item in scored[:limit]]


def preview_search(question: str, sources: tuple[Source, ...], limit: int = 2) -> list[Source]:
    query = terms(question)
    matches = [
        (2 * len(query & terms(item.title)) + len(query & terms(item.text)), item)
        for item in sources
    ]
    matches.sort(key=lambda match: match[0], reverse=True)
    return [item for score, item in matches[:limit] if score >= 3]


class VectorSearch:
    def __init__(self, embedding_client, sources: tuple[Source, ...], directory=INDEX_DIR):
        self.embedding_client = embedding_client
        self.sources = {source.id: source for source in sources}
        self.directory = directory
        self._collection = None
        self._lock = Lock()

    def _embeddings(self, inputs: list[str]):
        result = self.embedding_client.embeddings.create(model=EMBEDDING_MODEL, input=inputs)
        return [item.embedding for item in sorted(result.data, key=lambda item: item.index)]

    def _get_collection(self):
        with self._lock:
            if self._collection is not None:
                return self._collection
            import chromadb

            db = chromadb.PersistentClient(path=str(self.directory))
            collection = db.get_or_create_collection(
                "scu_datascience", embedding_function=None, configuration={"hnsw": {"space": "cosine"}}
            )
            stored = collection.get(include=["metadatas"])
            hashes = {key: meta["hash"] for key, meta in zip(stored["ids"], stored["metadatas"])}
            changed = []
            for source in self.sources.values():
                revision = sha256(
                    repr((EMBEDDING_MODEL, source.title, source.url, source.text)).encode()
                ).hexdigest()
                if hashes.get(source.id) != revision:
                    changed.append((source, revision))
            for offset in range(0, len(changed), 48):
                batch = changed[offset:offset + 48]
                collection.upsert(
                    ids=[source.id for source, _ in batch],
                    documents=[source.text for source, _ in batch],
                    embeddings=self._embeddings(
                        [f"{source.title}\n{source.text}" for source, _ in batch]
                    ),
                    metadatas=[
                        {"title": source.title, "url": source.url, "hash": revision}
                        for source, revision in batch
                    ],
                )
            retired = list(set(hashes) - self.sources.keys())
            if retired:
                collection.delete(ids=retired)
            self._collection = collection
            return collection

    def warm_up(self) -> None:
        """Open (and if needed refresh) the vector index ahead of the first question."""
        try:
            self._get_collection()
        except Exception:
            pass  # The first question retries and reports the failure to the user.

    @staticmethod
    def _course_programs(question: str) -> set[str]:
        """學制 the question is about; 學士班 unless it names a graduate programme (the site's main audience)."""
        programs = set()
        if re.search(r"在職|碩專|專班", question):
            programs.add("碩士在職專班")
        if "碩士班" in question or (not programs and re.search(r"碩士|研究所|碩[一二]", question)):
            programs.add("碩士班")
        if re.search(r"學士|大學部|大[一二三四]", question):
            programs.add("學士班")
        return programs or {"學士班"}

    def _course_years(self, question: str, programs: set[str] | None = None) -> set[str]:
        """Course-table years to keep: those named in the question, else the latest one."""
        available = {
            match.group(1) for item in self.sources.values()
            if (match := COURSE_YEAR.search(item.title))
            and (programs is None or (found := COURSE_PROGRAM.search(item.title)) and found.group(1) in programs)
        }
        asked = set(re.findall(r"(1\d\d)\s*(?:學年|年入學|級)", question)) & available
        return asked or ({max(available)} if available else set())

    def search(self, question: str, limit: int = 6) -> list[Source]:
        # 「教授什麼／哪些課」 means "teach"; written as 教, it no longer pulls in the professors' profiles.
        question = TEACH_VERB.sub("教", question)
        if any(word in question for word in LIST_WORDS):
            for page, topics in LIST_PAGES.items():
                if topics.search(question):
                    listed = [item for item in self.sources.values() if item.page == page]
                    if listed:
                        return listed
        collection = self._get_collection()
        result = collection.query(
            query_embeddings=self._embeddings([question]),
            # Each course-table passage exists once per 學制 and 入學年度; fetch extra so the others can be dropped.
            n_results=min(limit * 8, len(self.sources)),
            include=[],
        )
        programs = self._course_programs(question)
        years = self._course_years(question, programs)

        def wanted(key):
            title = self.sources[key].title
            match = COURSE_YEAR.search(title)
            if match is None:
                return True
            program = COURSE_PROGRAM.search(title)
            return match.group(1) in years and (program is None or program.group(1) in programs)

        named = [item.id for item in self.sources.values() if any(name in question for name in item.names)]
        vector = [key for key in result["ids"][0] if key in self.sources and wanted(key)]
        # Long course lists embed poorly for a single course name, so add passages naming a matching course.
        keyword = [item.id for item in course_matches(
            question, [item for item in self.sources.values() if wanted(item.id)]
        )]
        ids = list(dict.fromkeys([*named, *vector[:limit - len(keyword)], *keyword, *vector]))[:limit]
        return [self.sources[key] for key in ids]
