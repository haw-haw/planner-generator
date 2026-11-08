"""Generate printable planners (A5 and A6) and their saddle-stitch booklet impositions."""

import calendar
import datetime as dt
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from lunar_python import Solar
from pypdf import PageObject, PdfReader, PdfWriter, Transformation

YEAR = 2027
MIN_NOTES_PAGES = 1
MM = 72 / 25.4

ROOT = Path(__file__).parent
BUILD = ROOT / "build"
OUTPUT = ROOT / "output"
CHROME = os.environ.get(
    "CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)


@dataclass(frozen=True)
class Format:
    """Page geometry in mm. Must stay in sync with the matching CSS file."""

    name: str
    sheet: str
    css: tuple
    width: float
    height: float
    content_w: float
    content_h: float
    header: float
    line: float
    month_grid_top: float
    month_grid_head: float
    week_gap: float
    day_head: float
    goal_lines: int
    todo_lines: int
    habit_rows: int
    review_lines: int
    info_goals: int


FORMATS = [
    Format(
        name="A5", sheet="A4", css=("style.css",), width=148, height=210,
        content_w=128, content_h=192, header=16, line=6,
        month_grid_top=2, month_grid_head=6, week_gap=3, day_head=7,
        goal_lines=5, todo_lines=6, habit_rows=6, review_lines=5, info_goals=10,
    ),
    Format(
        name="A6", sheet="A5", css=("style.css", "style-a6.css"), width=105, height=148,
        content_w=90, content_h=135, header=11, line=5,
        month_grid_top=1.5, month_grid_head=5, week_gap=2, day_head=5.5,
        goal_lines=4, todo_lines=4, habit_rows=5, review_lines=4, info_goals=8,
    ),
]

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]
MONTH_EN = [calendar.month_name[i].upper() for i in range(13)]
LUNAR_FESTIVALS = {"除夕", "春节", "元宵节", "端午节", "七夕节", "中秋节", "重阳节", "腊八节"}
SOLAR_FESTIVALS = {
    "元旦节": "元旦", "情人节": "情人节", "妇女节": "妇女节", "植树节": "植树节",
    "劳动节": "劳动节", "青年节": "青年节", "儿童节": "儿童节", "建党节": "建党节",
    "建军节": "建军节", "教师节": "教师节", "国庆节": "国庆节", "圣诞节": "圣诞节",
    "母亲节": "母亲节", "父亲节": "父亲节",
}

_holidays = json.loads((ROOT / "holidays.json").read_text(encoding="utf-8"))
OFF_DAYS = {dt.date.fromisoformat(s) for s in _holidays["off"]}
WORK_DAYS = {dt.date.fromisoformat(s) for s in _holidays["work"]}


def day_label(d):
    solar = Solar.fromYmd(d.year, d.month, d.day)
    lunar = solar.getLunar()
    fests = [f for f in lunar.getFestivals() if f in LUNAR_FESTIVALS]
    fests += [SOLAR_FESTIVALS[f] for f in solar.getFestivals() if f in SOLAR_FESTIVALS]
    if fests:
        return fests[0], "fest"
    if lunar.getJieQi():
        return lunar.getJieQi(), "term"
    if lunar.getDay() == 1:
        return lunar.getMonthInChinese() + "月", "lunar"
    return lunar.getDayInChinese(), "lunar"


def day_class(d):
    if d in OFF_DAYS:
        return "off"
    if d in WORK_DAYS:
        return "work"
    if d.weekday() >= 5:
        return "we"
    return ""


def badge(d):
    if d in OFF_DAYS:
        return '<span class="badge off">休</span>'
    if d in WORK_DAYS:
        return '<span class="badge work">班</span>'
    return ""


def lines(n, cls="line"):
    return "".join(f'<div class="{cls}"></div>' for _ in range(n))


def checks(n):
    return "".join('<div class="line check"><i></i></div>' for _ in range(n))


def month_weeks(year, month):
    """Rows of 7 dates (Monday first) covering the month."""
    return calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)


# ---------------------------------------------------------------- pages


def header(big, cn="", en="", right=""):
    return (
        f'<div class="hdr"><div class="ttl"><span class="big num">{big}</span>'
        f'<span class="cn">{cn}</span><span class="en">{en}</span></div>'
        f'<div class="hr num">{right}</div></div>'
    )


def cover(f):
    return (
        f'<div class="cover"><div class="cv-year num">{YEAR}</div>'
        '<div class="cv-sub">PLANNER</div><div class="cv-cn">手 帐</div></div>'
        '<div class="cv-name"><span>NAME</span><div class="line"></div></div>'
    )


def info_page(f):
    fields = ["姓名", "电话", "邮箱", "地址", "紧急联系人"]
    rows = "".join(
        f'<div class="field"><span>{name}</span><div></div></div>' for name in fields
    )
    goals = "".join(
        f'<div class="line goal"><span class="num">{i}</span></div>'
        for i in range(1, f.info_goals + 1)
    )
    return (
        header("个人信息", en="ABOUT ME", right=str(YEAR))
        + f'<div class="fields">{rows}</div>'
        + '<div class="lost">如果拾获本手帐，请联系上方电话，万分感谢！</div>'
        + f'<div class="sec"><div class="st">{YEAR} 年度目标</div>{goals}</div>'
        + '<div class="sec"><div class="st">年度关键词</div><div class="kw"></div></div>'
    )


def mini_month(year, month, highlight=True):
    rows = ""
    for week in month_weeks(year, month):
        cells = ""
        for d in week:
            if d.month != month:
                cells += "<td></td>"
            else:
                cls = day_class(d) if highlight else ("we" if d.weekday() >= 5 else "")
                cells += f'<td class="{cls}">{d.day}</td>'
        rows += f"<tr>{cells}</tr>"
    head = "".join(
        f'<th class="{"we" if i >= 5 else ""}">{w}</th>' for i, w in enumerate(WEEKDAYS)
    )
    return (
        f'<div class="mini"><div class="mt"><b class="num">{month}</b>月'
        f'<span>{MONTH_EN[month][:3]}</span></div>'
        f'<table class="num"><tr>{head}</tr>{rows}</table></div>'
    )


def year_page(f, year):
    minis = "".join(mini_month(year, m, highlight=(year == YEAR)) for m in range(1, 13))
    legend = (
        '<div class="legend"><span class="off">■</span> 法定节假日　'
        "放假调休安排以国务院办公厅通知为准</div>"
        if year == YEAR
        else ""
    )
    return header(str(year), cn="年历", en="CALENDAR") + f'<div class="year">{minis}</div>' + legend


def month_left(f, month):
    weeks = month_weeks(YEAR, month)
    rows_total = f.content_h - f.header - f.month_grid_top - f.month_grid_head - 3
    row_h = rows_total / len(weeks)
    head = "<th></th>" + "".join(
        f'<th class="{"we" if i >= 5 else ""}">{w}</th>' for i, w in enumerate(WEEKDAYS)
    )
    body = ""
    for week in weeks:
        wk = week[0].isocalendar()[1]
        cells = f'<td class="wk num">W{wk:02d}</td>'
        for d in week:
            if d.month != month:
                cells += f'<td class="out"><div class="dn num">{d.day}</div></td>'
                continue
            text, kind = day_label(d)
            cells += (
                f'<td class="{day_class(d)}"><div class="dn num">{d.day}{badge(d)}</div>'
                f'<div class="lu {kind}">{text}</div></td>'
            )
        body += f'<tr style="height:{row_h:.2f}mm">{cells}</tr>'
    return (
        header(str(month), cn="月", en=MONTH_EN[month], right=str(YEAR))
        + f'<table class="mgrid"><colgroup><col class="wkcol">{"<col>" * 7}</colgroup>'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def month_right(f, month):
    days = calendar.monthrange(YEAR, month)[1]
    dates = [dt.date(YEAR, month, i) for i in range(1, days + 1)]
    head = '<th class="hn">习惯</th>' + "".join(
        f'<th class="{"we" if d.weekday() >= 5 else ""}">{d.day}</th>' for d in dates
    )
    row = "<td></td>" + "".join(
        f'<td class="{"we" if d.weekday() >= 5 else ""}"></td>' for d in dates
    )
    habits = f"<tr>{head}</tr>" + f"<tr>{row}</tr>" * f.habit_rows
    return (
        header("计划", en="MONTHLY PLAN", right=f"{month}月")
        + f'<div class="sec"><div class="st">本月目标</div>{lines(f.goal_lines)}</div>'
        + f'<div class="sec"><div class="st">待办事项</div><div class="cols">'
        f"<div>{checks(f.todo_lines)}</div><div>{checks(f.todo_lines)}</div></div></div>"
        + f'<div class="sec"><div class="st">习惯打卡</div>'
        f'<table class="habit num">{habits}</table></div>'
        + f'<div class="sec"><div class="st">月末回顾</div>{lines(f.review_lines)}</div>'
    )


def week_page(f, monday):
    sunday = monday + dt.timedelta(days=6)
    iso_year, wk, _ = monday.isocalendar()
    title = f"W{wk:02d}" if iso_year == YEAR else f"{iso_year} W{wk:02d}"
    span = f"{monday.month}.{monday.day:02d} – {sunday.month}.{sunday.day:02d}"
    row_h = (f.content_h - f.header - f.week_gap) / 4
    n_lines = int((row_h - f.day_head) // f.line)
    cells = ""
    for i in range(7):
        d = monday + dt.timedelta(days=i)
        text, kind = day_label(d)
        cells += (
            f'<div class="day {day_class(d)}"><div class="dh">'
            f'<span class="dn num">{d.day}</span><span class="wd">周{WEEKDAYS[i]}</span>'
            f'{badge(d)}<span class="lu {kind}">{text}</span></div>{lines(n_lines)}</div>'
        )
    cells += (
        '<div class="day todo"><div class="dh"><span class="wd">本周重点</span></div>'
        f"{checks(n_lines)}</div>"
    )
    return (
        header(title, cn="", en=f"{MONTH_EN[monday.month][:3]} {monday.year}", right=span)
        + f'<div class="week" style="grid-template-rows:repeat(4,{row_h:.2f}mm)">{cells}</div>'
    )


def notes_page(f):
    step = 5
    h = f.content_h - f.header - 3 - 3
    cols = int((f.content_w - 2) // step) + 1
    rows = int((h - 2) // step) + 1
    vw, vh = (cols - 1) * step + 2, (rows - 1) * step + 2
    dots = "".join(
        f'<circle cx="{x * step}" cy="{y * step}" r="0.28"/>'
        for y in range(rows) for x in range(cols)
    )
    return (
        header("笔记", en="NOTES")
        + f'<svg class="dots" viewBox="-1 -1 {vw} {vh}" width="{vw}mm" height="{vh}mm">{dots}</svg>'
    )


def back_cover(f):
    return f'<div class="back num">{YEAR} PLANNER</div>'


# ---------------------------------------------------------------- assembly


def week_mondays():
    monday = dt.date(YEAR, 1, 1) - dt.timedelta(days=dt.date(YEAR, 1, 1).weekday())
    while monday <= dt.date(YEAR, 12, 31):
        yield monday
        monday += dt.timedelta(days=7)


def week_month(monday):
    """Assign each week to the month of its Thursday, clamped to YEAR."""
    thursday = monday + dt.timedelta(days=3)
    if thursday.year < YEAR:
        return 1
    if thursday.year > YEAR:
        return 12
    return thursday.month


def build_pages(f):
    pages = [("cover", cover(f)), ("", info_page(f)), ("", year_page(f, YEAR))]
    by_month = {m: [] for m in range(1, 13)}
    for monday in week_mondays():
        by_month[week_month(monday)].append(monday)
    for m in range(1, 13):
        # Monthly spread must start on an even (left-hand) page.
        if len(pages) % 2 == 0:
            pages.append(("", notes_page(f)))
        pages += [("", month_left(f, m)), ("", month_right(f, m))]
        pages += [("", week_page(f, mon)) for mon in by_month[m]]
    tail = [("", year_page(f, YEAR + 1))]
    notes = MIN_NOTES_PAGES
    while (len(pages) + len(tail) + notes + 1) % 4:
        notes += 1
    pages += tail + [("", notes_page(f))] * notes + [("back", back_cover(f))]
    return pages


def render_html(f, pages):
    css = "".join((ROOT / name).read_text(encoding="utf-8") for name in f.css)
    body = ""
    for i, (cls, html) in enumerate(pages, start=1):
        side = "right" if i % 2 else "left"
        body += f'<section class="page {side} {cls}">{html}</section>\n'
    return f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'


def html_to_pdf(html_path, pdf_path):
    subprocess.run(
        [
            CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            f"--user-data-dir={BUILD / 'chrome-profile'}",
            f"--print-to-pdf={pdf_path}", html_path.as_uri(),
        ],
        check=True, capture_output=True,
    )


def saddle_stitch_sides(n):
    """All sheets nested and folded together; the outer sheet carries 1, 2, n-1, n."""
    for i in range(n // 4):
        yield n - 2 * i, 1 + 2 * i
        yield 2 + 2 * i, n - 1 - 2 * i


def folded_sheet_sides(n):
    """Each sheet folded on its own and stacked; sheet i carries pages 4i+1 .. 4i+4."""
    for base in range(0, n, 4):
        yield base + 4, base + 1
        yield base + 2, base + 3


def impose(f, src, dst, sides):
    """Lay out pages two-up on a landscape sheet as (left, right) pairs per side (duplex, flip on short edge)."""
    reader = PdfReader(src)
    n = len(reader.pages)
    assert n % 4 == 0, f"page count {n} is not a multiple of 4"
    sheet_w, sheet_h = 2 * f.width * MM, f.height * MM
    writer = PdfWriter()
    for left, right in sides(n):
        sheet = PageObject.create_blank_page(width=sheet_w, height=sheet_h)
        for idx, x0 in [(left, 0), (right, sheet_w / 2)]:
            page = reader.pages[idx - 1]
            pw, ph = float(page.mediabox.width), float(page.mediabox.height)
            tx = x0 + (sheet_w / 2 - pw) / 2 - float(page.mediabox.left)
            ty = (sheet_h - ph) / 2 - float(page.mediabox.bottom)
            sheet.merge_transformed_page(page, Transformation().translate(tx, ty))
        writer.add_page(sheet)
    writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    with open(dst, "wb") as fh:
        writer.write(fh)
    return n


def build(f, impose_only=False):
    single = OUTPUT / f"planner-{YEAR}-{f.name}.pdf"
    if not impose_only:
        pages = build_pages(f)
        html_path = BUILD / f"planner-{f.name}.html"
        html_path.write_text(render_html(f, pages), encoding="utf-8")
        html_to_pdf(html_path, single)
        rendered = len(PdfReader(single).pages)
        if rendered != len(pages):
            sys.exit(f"{f.name}: expected {len(pages)} pages but Chrome rendered {rendered}; check for overflow")
    print(f"{f.name}: {single}")
    for suffix, sides in [("booklet", saddle_stitch_sides), ("folded", folded_sheet_sides)]:
        dst = OUTPUT / f"planner-{YEAR}-{f.sheet}-{suffix}.pdf"
        n = impose(f, single, dst, sides)
        print(f"  {n // 4} {f.sheet} sheets (duplex) -> {dst}")


def main():
    BUILD.mkdir(exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    args = sys.argv[1:]
    impose_only = "--impose-only" in args
    wanted = {a.upper() for a in args if not a.startswith("--")}
    for f in FORMATS:
        if not wanted or f.name in wanted:
            build(f, impose_only)


if __name__ == "__main__":
    main()
