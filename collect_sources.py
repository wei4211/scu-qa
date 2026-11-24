"""Refresh the knowledge base from public SCU department pages and the saved course tables.

Course tables (必選修科目表) are read from data/必選修科目表/<學制>/<學年度>學年度.pdf rather than
downloaded, so they can be checked by hand and the update still works when a link breaks.
A scanned PDF has no text layer; put a hand-checked「<學年度>學年度_文字版.csv」 beside it.
"""

import json
import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from course_tables import PROGRAMS, course_passages
from sources import DATA_FILE

SITE = "https://web-ch.scu.edu.tw"
PAGES = (
    ("辦學特色", "/datascience/web_page/16154", "article"),
    ("考生常見問答", "/datascience/faq/16799", "faq"),
    ("必選修科目表", "/datascience/web_page/16212", "article"),
    ("碩士班必選修科目表", "/datascience/web_page/16246", "article"),
    ("碩士在職專班必選修科目表", "/datascience/web_page/16252", "article"),
    ("專任師資", "/datascience/teacher_resume/16062", "faculty"),
    ("跨域實驗室", "/index.php/datascience/web_page/16199", "article"),
    ("學生專題影音", "/datascience/web_page/16207", "article"),
    ("企業實習修課說明", "/datascience/web_page/16231", "article"),
    ("畢業出路", "/datascience/web_page/16196", "article"),
    ("大學申請入學", "/datascience/web_page/16142", "article"),
    ("系辦聯絡資訊", "/datascience", "footer"),
)
COURSE_PAGE = "必選修科目表"
# Department page that links each 學制's yearly course tables (used as the passages' source link).
COURSE_LINK_PAGES = {"必選修科目表": "學士班", "碩士班必選修科目表": "碩士班", "碩士在職專班必選修科目表": "碩士在職專班"}
COURSE_DIR = DATA_FILE.parent / "必選修科目表"
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
GENERIC_LINK_TEXT = ("連結", "link", "點此", "這裡", "下載")


def clean(node):
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def file_links(node, page_url, fallback):
    """Name the "連結" style anchors in a node, e.g. each year's course table PDF."""
    links = []
    for anchor in node.select("a[href]"):
        if clean(anchor).lower() not in GENERIC_LINK_TEXT:
            continue
        label = ""
        for sibling in anchor.previous_siblings:
            if getattr(sibling, "name", None) == "a":
                break
            label = (sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling)) + label
        label = re.sub(r"\s+", " ", label).strip(" ()（）:：、")
        label = label.rsplit(")", 1)[-1].rsplit("）", 1)[-1].strip(" ()（）:：、")
        links.append({"title": label or fallback, "url": urljoin(page_url, anchor["href"])})
    return links


def extract(body, kind, page_url):
    if kind == "faculty":
        for row in body.select("table tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) == 5 and cells[1].find("a") and clean(cells[4]):
                name = clean(cells[1])
                yield name, f"姓名：{name}｜職稱：{clean(cells[0])}｜專長領域：{clean(cells[4])}", [name.split()[0]], []
        return
    if kind == "faq":
        for panel in body.select(".panel"):
            title = panel.select_one(".panel-heading")
            answer = panel.select_one(".panel-body #article") or panel.select_one(".panel-body")
            if title and answer and clean(answer):
                yield clean(title), clean(answer), [], []
        return

    if kind == "footer":
        text = clean(body).split("社群帳號", 1)[0]
        if "聯絡我們" in text and "電話" in text:
            yield "聯絡我們", text[text.index("聯絡我們"):], [], []
        return

    title = ""
    parts = []
    links = []
    for node in body.find_all([*HEADINGS, "p", "li"]):
        if node.find_parent(["p", "li"]) or node.find_parent(class_="pagination"):
            continue
        text = clean(node)
        if not text:
            continue
        if node.name in HEADINGS or text.lower() == "stark lab":
            if parts:
                yield title, "\n".join(parts), [], links
                parts, links = [], []
            title = text
        else:
            parts.append(text)
            links.extend(file_links(node, page_url, title))
    if parts:
        yield title, "\n".join(parts), [], links
    if kind == "article" and body.select_one('a[href*="entrance"], a[href*="gm.scu.edu.tw/entrance"]'):
        links = [clean(node) for node in body.select("p,li") if "備審資料準備指引" in clean(node)]
        if links:
            yield "備審資料準備指引", "\n".join(dict.fromkeys(links)), [], []


def course_files() -> list[tuple[str, str, Path]]:
    """(學制, 學年度, file) for every saved course table, preferring a CSV transcription over its PDF."""
    found = []
    for program in PROGRAMS:
        for pdf in sorted((COURSE_DIR / program).glob("*學年度.pdf")):
            year = pdf.stem[:3]
            transcript = pdf.with_name(f"{pdf.stem}_文字版.csv")
            found.append((program, year, transcript if transcript.exists() else pdf))
    if not found:
        raise ValueError(f"找不到科目表：請把 PDF 放在 {COURSE_DIR}/<學制>/<學年度>學年度.pdf")
    return found


def collect():
    records = {}
    course_links = {}
    with requests.Session() as session:
        for title, path, kind in PAGES:
            pending = [urljoin(SITE, path)]
            visited = set()
            count = 0
            seen_texts = set()
            for url in pending:
                if url in visited:
                    continue
                visited.add(url)
                response = session.get(url, timeout=20)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                body = soup.select_one("footer" if kind == "footer" else "#rndbox_body")
                if body is None:
                    raise ValueError(f"找不到系網正文：{url}")
                if kind == "faculty":
                    for link in body.select(".pagination a[href]"):
                        other = urljoin(url, link["href"])
                        parsed = urlsplit(other)
                        page = parse_qs(parsed.query).get("page", ["1"])[0]
                        if parsed.netloc == urlsplit(SITE).netloc and parsed.path == path and page != "1" and other not in pending:
                            pending.append(other)
                for section, full_text, names, links in extract(body, kind, url):
                    for offset in range(0, len(full_text), 630):
                        text = full_text[offset:offset + 680].strip()
                        if not text or text in seen_texts:
                            continue
                        seen_texts.add(text)
                        key = sha256(f"{url}\n{section}\n{text}".encode()).hexdigest()[:20]
                        records[key] = {
                            "id": key, "page": title, "title": f"{title}｜{section}" if section else title,
                            "url": url, "text": text, "names": names, "links": links,
                        }
                        count += 1
                    if title in COURSE_LINK_PAGES:
                        for link in links:
                            year = re.search(r"(\d{3})學年度", link["title"])
                            if year:
                                course_links[(COURSE_LINK_PAGES[title], year.group(1))] = link["url"]
                        course_links.setdefault((COURSE_LINK_PAGES[title], ""), url)
            if not count:
                raise ValueError(f"找不到可索引資料：{title}")
            print(f"{title}：{count} 段")
    for program, year, path in course_files():
        source = path.read_text(encoding="utf-8-sig") if path.suffix == ".csv" else path.read_bytes()
        passages, check = course_passages(year, source, program)
        # Link answers to the official file for that year, or to the 學制's course-table page.
        url = course_links.get((program, year)) or course_links[(program, "")]
        for section, text in passages:
            key = sha256(f"{program}\n{year}\n{section}\n{text}".encode()).hexdigest()[:20]
            records[key] = {
                "id": key, "page": COURSE_PAGE, "title": f"{COURSE_PAGE}｜{section}",
                "url": url, "text": text, "names": [], "links": [],
            }
        print(f"{program} {year}學年度（{path.name}）：{len(passages)} 段，{check}")
    temp = DATA_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(list(records.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(DATA_FILE)
    print(f"共保存 {len(records)} 段公開系網資料。")


if __name__ == "__main__":
    collect()
