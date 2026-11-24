"""Turn the university's yearly 學雜費收費標準一覽表 PDF into passages about the 資料科學系 fees.

The PDF covers every college; only the 巨資學院資料科學系 rows, the 碩士班 rules and the
other fees that apply to every student (computer use, dormitories) are kept. All amounts are
in NT$ per semester, as the PDF states.
"""

import io
import re

import pdfplumber

SOURCE_PAGE = "https://finance.scu.edu.tw/node/49"
NUMBER = r"([\d,]+|-)"


def _text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def _section(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    stop = text.find(end, begin)
    return text[begin:stop if stop != -1 else None]


def _notes(section: str) -> str:
    """The 註 paragraphs of a section joined into plain sentences (the PDF breaks lines mid-sentence).

    Notes about another department's programme (e.g. 法學院「國際經貿談判碩士在職專班」) are left out.
    """
    notes = re.findall(r"註\d：.*?(?=註\d：|$)", section, flags=re.S)
    joined = (re.sub(r"\s*\n\s*", "", note).strip() for note in notes)
    return "\n".join(note for note in joined if "國際經貿談判" not in note)


def tuition_passages(year: str, pdf_bytes: bytes) -> list[tuple[str, str]]:
    """(section title, text) pairs for one 學年度; raises ValueError if the PDF layout has changed."""
    text = _text(pdf_bytes)
    head = f"{year}學年度學雜費收費標準（新臺幣，每學期）"

    undergraduate = re.search(r"巨資學院資料科學系（含學位\s*" + r"\s+".join([NUMBER] * 6), text)
    in_service = re.search(r"巨資學院資料科學系（含學位學程）\s+" + r"\s+".join([NUMBER] * 3), text)
    if not undergraduate or not in_service:
        raise ValueError(f"{year}學年度學雜費表找不到資料科學系的收費列，請檢查 PDF 格式是否改變")
    fee, fee_cn, late_fee, late_fee_cn, credit, credit_cn = undergraduate.groups()
    per_credit, per_credit_after_37, misc = in_service.groups()

    bachelor_notes = _notes(_section(text, "一、學士班", "二、碩、博士班"))
    master_rules = re.sub(r"\s*\n\s*", "", _section(text, "二、碩、博士班", "三、碩士在職專班"))
    in_service_notes = _notes(_section(text, "三、碩士在職專班", "四、進修學士班"))
    thesis_fee = re.search(r"論文指導費-碩士在職專班學生申請學位考試時繳交\s*([\d,]+)", text)

    other = _section(text, "五、其他收費項目", "\x00")
    other_lines = [
        f"{item}：{amount} 元" for item, amount in re.findall(r"^(\S[^\n]*?)\s+([\d,]+)$", other, flags=re.M)
        if not item.startswith("音樂指導費")  # applies to the music department only
    ]

    return [
        (f"學雜費｜{year}學年度｜學士班", (
            f"{head}：巨資學院資料科學系學士班（含學位學程及學士後）\n"
            f"• 修業年限內學雜費：一般生 {fee} 元、大陸生 {fee_cn} 元\n"
            f"• 延修生每學期修 10 學分以上：一般生 {late_fee} 元、大陸生 {late_fee_cn} 元\n"
            f"• 延修生每學期修 9 學分以下，繳學分費每學分：一般生 {credit} 元、大陸生 {credit_cn} 元\n"
            f"{bachelor_notes}"
        )),
        (f"學雜費｜{year}學年度｜碩士班", (
            f"{head}：資料科學系碩士班一、二年級學雜費比照學士班，一般生每學期 {fee} 元、大陸生 {fee_cn} 元。\n"
            f"原文規定：{master_rules}"
        )),
        (f"學雜費｜{year}學年度｜碩士在職專班", (
            f"{head}：巨資學院資料科學系碩士在職專班（含學位學程）\n"
            f"• 學分費每學分 {per_credit} 元；累計 37 學分（含）以上每學分 {per_credit_after_37} 元\n"
            f"• 雜費每學期 {misc} 元\n"
            + (f"• 論文指導費 {thesis_fee.group(1)} 元（申請學位考試時繳交）\n" if thesis_fee else "")
            + in_service_notes
        )),
        (f"學雜費｜{year}學年度｜其他費用與宿舍", (
            f"{head}：全校共通的其他收費項目，包含電腦及網路通訊使用費與學生宿舍費。\n" + "\n".join(other_lines)
        )),
    ]
