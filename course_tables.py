"""Turn the department's yearly 必選修科目表 PDFs into readable course passages.

Each PDF table row holds: 科目名稱 | 選別 | 學分 | 8 semester columns (大一上 … 大四下) | 備註.
Passages are grouped by 入學年度, study year and 必修/選修 so that a question such as
「大一要修哪些課？」 retrieves one compact list instead of scattered rows.
"""

import io
import re

import pdfplumber

SEMESTERS = ("大一上", "大一下", "大二上", "大二下", "大三上", "大三下", "大四上", "大四下")
STUDY_YEARS = ("大一", "大二", "大三", "大四")
CJK = r"㐀-鿿"


def _lines(cell) -> list[str]:
    return [line.strip() for line in (cell or "").split("\n") if line.strip()]


def _chinese_part(cell) -> str:
    """Keep the Chinese lines of a bilingual cell (Chinese comes first, English follows)."""
    kept = []
    for line in _lines(cell):
        if not re.search(f"[{CJK}]", line):
            break
        kept.append(re.sub(r"\s*[A-Za-z][A-Za-z .,'’()/-]*$", "", line))
    return re.sub(r"\s+", "", "".join(kept))


def _course_name(cell) -> str:
    lines = _lines(cell)
    if not lines:
        return ""
    name = lines[0]
    # Overlapping text layers interleave letters into the Chinese title, e.g. 「I時NN間OV序AT列ION分」.
    if len(re.findall(f"[{CJK}][A-Za-z]|[A-Za-z][{CJK}]", name)) >= 4:
        name = "".join(re.findall(f"[{CJK}()（）一二三四]", name))
    else:
        name = re.sub(r"(?<=[^\x00-\x7f])\s+(?=[^\x00-\x7f])", "", name).strip()
        # Strip the English title when it shares the first line, e.g. 「區塊鏈 BLOCKCHAIN …」.
        name = re.sub(r"\s+[A-Z][A-Z &/(),.-]{3,}$", "", name)
    return name


def _columns(header: list) -> tuple[int, int] | None:
    """Locate the 選別 and 學分 columns from the first header row."""
    kind = credit = None
    for index, cell in enumerate(header):
        text = re.sub(r"\s+", "", cell or "")
        if kind is None and "選" in text and ("別" in text or "lective" in text):
            kind = index
        elif kind is not None and credit is None and "學" in text and "分" in text:
            credit = index
    if kind is None or credit is None or credit != kind + 1 or len(header) < credit + 10:
        return None
    return kind, credit


def _totals(rows: list[list], text: str) -> str:
    totals = {}
    for row in rows:
        cells = [re.sub(r"\s+", "", cell or "") for cell in row]
        label = next((cell[:2] for cell in cells if re.match(r"(必修|選修|共計)(Required|Elective|Total)?$", cell)), None)
        number = next((cell for cell in cells if re.fullmatch(r"\d{2,3}", cell)), None)
        if label and number:
            totals.setdefault(label, number)
    if len(totals) < 3 and "畢業學分總計" in text:
        # Older PDFs merge the three total rows into one cell; read them from the page text instead.
        tail = text[text.rindex("畢業學分總計") - 120:text.rindex("畢業學分總計") + 200]
        for label in ("必修", "選修", "共計"):
            match = re.search(label + r"\s*(?:Required|Elective|Total)?\s*(\d{2,3})(?!\d)", tail)
            if match:
                totals.setdefault(label, match.group(1))
    if len(totals) < 2:
        return ""
    return "畢業學分總計：" + "、".join(f"{key} {totals[key]} 學分" for key in ("必修", "選修", "共計") if key in totals)


def _tables(page) -> list[list[list]]:
    """Tables on a page, plus a last row that pdfplumber drops when the page ends without a bottom border."""
    tables = []
    footer = min((word["top"] for word in page.extract_words() if word["text"] == "Page"), default=page.height)
    for found in page.find_tables():
        rows = found.extract()
        left, _, right, bottom = found.bbox
        if bottom < footer - 8:
            bounds = sorted({round(cell[0], 1) for cell in found.cells} | {round(cell[2], 1) for cell in found.cells})
            words = page.crop((left, bottom + 1, right, footer - 1)).extract_words()
            if words and rows:
                columns = [[] for _ in rows[0]]
                for word in sorted(words, key=lambda item: (round(item["top"]), item["x0"])):
                    middle = (word["x0"] + word["x1"]) / 2
                    index = sum(1 for edge in bounds[1:-1] if edge <= middle)
                    columns[min(index, len(columns) - 1)].append(word)
                orphan = []
                for column in columns:
                    lines = {}
                    for word in column:
                        lines.setdefault(round(word["top"] / 3), []).append(word["text"])
                    orphan.append("\n".join(" ".join(parts) for _, parts in sorted(lines.items())) or None)
                rows.append(orphan)
        tables.append(rows)
    return tables


def parse_courses(pdf_bytes: bytes) -> tuple[list[dict], str, str]:
    """Return (courses, graduation-credit summary, notes) parsed from one curriculum PDF."""
    courses = []
    total_rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            for table in _tables(page):
                if not table or (positions := _columns(table[0])) is None:
                    continue
                kind_col, credit_col = positions
                width = len(table[0])
                semester_cols = range(credit_col + 1, credit_col + 9)
                parent = None
                for row in table:
                    cells = list(row) + [None] * (width - len(row))
                    if any("畢業學分" in (cell or "") for cell in cells) or any(
                        re.match(r"(必修|選修|共計)", re.sub(r"\s+", "", cell or "")) for cell in cells[1:credit_col]
                    ):  # column 0 is the category label, e.g. a vertical 「必修」 beside 微積分
                        total_rows.append(cells)
                        continue
                    kind = _chinese_part(cells[kind_col])
                    # Column 0 holds the vertical category label (校訂共同必修…) when the name sits in column 1.
                    name_col = 1 if kind_col >= 2 else 0
                    main = _course_name(cells[name_col])
                    sub = _chinese_part(cells[name_col + 1]) if name_col + 1 < kind_col else ""
                    if kind in ("必", "選") and main:
                        parent = {"name": main, "kind": kind, "credits": re.sub(r"\s+", "", cells[credit_col] or "")}
                        credits = parent["credits"]
                        name = sub or main
                    elif not main and sub and parent:
                        # Continuation row such as 外文(二) under the merged 外文 cell.
                        kind, name, credits = parent["kind"], sub, ""
                    else:
                        continue
                    schedule, remarks = [], []
                    for label, index in zip(SEMESTERS, semester_cols):
                        value = re.sub(r"\s+", "", cells[index] or "")
                        if re.fullmatch(r"\d+", value):
                            schedule.append((label, value))
                        elif value:
                            remarks.append(_chinese_part(cells[index]))
                    remarks.append(_chinese_part(cells[width - 1]))
                    if sub and name == sub and parent:
                        remarks.append(f"屬「{parent['name']}」，合計 {parent['credits']} 學分")
                    courses.append({
                        "name": name,
                        "kind": kind,
                        "credits": credits,
                        "schedule": schedule,
                        "remark": "；".join(dict.fromkeys(item for item in remarks if item)),
                    })
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    notes = ""
    match = re.search(r"附\s*註\s*(?:Notes)?\s*[:：]", text)
    if match:
        kept = [
            line.strip() for line in text[match.end():].split("\n")
            if re.search(f"[{CJK}]", line) and not re.search(r"Page \d+ of|學士班必、選修科目表|適用\d+學年度", line)
        ]
        notes = "".join(kept)
    return courses, _totals(total_rows, text), notes


def _describe(course: dict, years: tuple[str, ...] = STUDY_YEARS) -> str:
    when = "、".join(f"{label} {value} 學分" for label, value in course["schedule"] if label[:2] in years)
    kind = "必修" if course["kind"] == "必" else "選修"
    parts = [course["name"], f"{kind} {course['credits']} 學分" if course["credits"] else kind]
    if when:
        parts.append(when)
    if course["remark"]:
        parts.append(f"備註：{course['remark']}")
    return "｜".join(parts)


def credit_check(courses: list[dict], totals: str) -> str:
    """Compare the parsed required credits with the PDF's own 必修 total.

    「人工智慧跨域應用」 is satisfied by 「人工智慧導論」 (see its remark), so it is not counted twice.
    """
    parsed = sum(
        int(course["credits"]) for course in courses
        if course["kind"] == "必" and course["credits"].isdigit() and "人工智慧導論" not in course["remark"]
    )
    expected = re.search(r"必修 (\d+)", totals)
    if not expected:
        return f"必修 {parsed} 學分（科目表未列總計，無法核對）"
    status = "相符" if parsed == int(expected.group(1)) else "不符，請檢查解析結果"
    return f"必修 {parsed}/{expected.group(1)} 學分，{status}"


def course_passages(year: str, pdf_bytes: bytes) -> tuple[list[tuple[str, str]], str]:
    """(section title, text) pairs for one 入學年度's curriculum, plus a credit check message."""
    courses, totals, notes = parse_courses(pdf_bytes)
    if not courses:
        raise ValueError(f"{year}學年度科目表沒有解析到任何科目")
    prefix = f"{year}學年度入學新生適用"
    passages = []
    for study_year in STUDY_YEARS:
        for kind, label in (("必", "必修"), ("選", "選修")):
            rows = [
                _describe(course, (study_year,))
                for course in courses
                if course["kind"] == kind and any(sem[:2] == study_year for sem, _ in course["schedule"])
            ]
            if rows:
                passages.append((f"{year}學年度入學｜{study_year}{label}科目", f"{prefix}，{study_year}{label}科目：\n" + "\n".join(rows)))
    unscheduled = [_describe(course) for course in courses if not course["schedule"]]
    if unscheduled:
        passages.append((f"{year}學年度入學｜不限年級的必修與畢業門檻", f"{prefix}，未排定學期的必修科目與畢業門檻：\n" + "\n".join(unscheduled)))
    if totals:
        passages.append((f"{year}學年度入學｜畢業學分", f"{prefix}，{totals}。"))
    if notes:
        passages.append((f"{year}學年度入學｜科目表附註", f"{prefix}，科目表附註：\n{notes}"))
    return passages, f"{len(courses)} 門科目，{credit_check(courses, totals)}"
