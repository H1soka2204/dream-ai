from io import BytesIO
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm

from services.i18n import t


def build_result_pdf(result):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    fonts = _register_fonts(pdfmetrics, TTFont)
    palette = {
        "bg": HexColor("#f6f8fc"),
        "surface": HexColor("#ffffff"),
        "ink": HexColor("#172033"),
        "muted": HexColor("#68748a"),
        "line": HexColor("#dce4ef"),
        "navy": HexColor("#111827"),
        "blue": HexColor("#2563eb"),
        "sky": HexColor("#0ea5e9"),
        "violet": HexColor("#7c3aed"),
        "green": HexColor("#15803d"),
        "amber": HexColor("#b7791f"),
        "danger": HexColor("#dc2626"),
    }

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    page = {"number": 0}

    def new_page():
        if page["number"]:
            pdf.showPage()
        page["number"] += 1
        _draw_page_shell(pdf, width, height, margin, fonts, palette, page["number"])
        return height - 32 * mm

    def ensure_space(y, needed):
        if y - needed < 26 * mm:
            return new_page()
        return y

    y = new_page()
    _draw_cover_header(pdf, result, width, height, margin, fonts, palette)
    y = height - 84 * mm

    status_text = t("успешно пройден") if result.passed else t("нужно повторить")
    status_color = palette["green"] if result.passed else palette["amber"]

    _draw_score_card(pdf, margin, y, 64 * mm, 46 * mm, result, fonts, palette, status_color)
    _draw_summary_card(
        pdf,
        margin + 70 * mm,
        y,
        width - margin * 2 - 70 * mm,
        46 * mm,
        result,
        fonts,
        palette,
        status_text,
    )
    y -= 56 * mm

    if result.wrong_topics:
        y = _draw_section_title(pdf, margin, y, t("Слабые темы"), fonts, palette)
        y = _draw_tags(pdf, margin, y, [t(topic) for topic in result.wrong_topics], width - margin * 2, fonts, palette)
        y -= 8 * mm

    if result.recommendation:
        y = ensure_space(y, 54 * mm)
        y = _draw_recommendation(pdf, margin, y, width - margin * 2, result.recommendation, fonts, palette)

    y = ensure_space(y, 34 * mm)
    y = _draw_section_title(pdf, margin, y, t("Ответы и объяснения"), fonts, palette)
    for index, answer in enumerate(result.answers_payload, start=1):
        question = t(answer.get("question", ""))
        selected = t(answer.get("selected", ""))
        correct = t(answer.get("correct", ""))
        explanation = t(answer.get("explanation", ""))
        is_correct = bool(answer.get("is_correct"))
        card_height = _answer_card_height(
            pdf, question, selected, correct, explanation, width - margin * 2, fonts
        )
        y = ensure_space(y, card_height + 8 * mm)
        y = _draw_answer_card(
            pdf,
            margin,
            y,
            width - margin * 2,
            card_height,
            index,
            question,
            selected,
            correct,
            explanation,
            is_correct,
            fonts,
            palette,
        )
        y -= 6 * mm

    pdf.save()
    buffer.seek(0)
    return buffer


def _draw_page_shell(pdf, width, height, margin, fonts, palette, page_number):
    pdf.setFillColor(palette["bg"])
    pdf.rect(0, 0, width, height, stroke=0, fill=1)

    pdf.setFillColor(palette["navy"])
    pdf.rect(0, height - 24 * mm, width, 24 * mm, stroke=0, fill=1)
    pdf.setFillColor(palette["blue"])
    pdf.rect(0, height - 24 * mm, width, 2.5 * mm, stroke=0, fill=1)

    _draw_logo(pdf, margin, height - 19 * mm, 13 * mm, palette)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont(fonts["bold"], 10)
    pdf.drawString(margin + 17 * mm, height - 13 * mm, "AI Edu Test")
    pdf.setFillColor(HexColor("#cbd5e1"))
    pdf.setFont(fonts["regular"], 8)
    pdf.drawString(margin + 17 * mm, height - 17 * mm, t("Персональный отчёт"))

    pdf.setFillColor(palette["muted"])
    pdf.setFont(fonts["regular"], 8)
    pdf.drawRightString(width - margin, 12 * mm, f"{t('Страница')} {page_number}")


def _draw_cover_header(pdf, result, width, height, margin, fonts, palette):
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.roundRect(margin, height - 72 * mm, width - margin * 2, 38 * mm, 6 * mm, stroke=0, fill=1)

    pdf.setFillColor(palette["blue"])
    pdf.roundRect(margin, height - 72 * mm, 5 * mm, 38 * mm, 2 * mm, stroke=0, fill=1)

    pdf.setFillColor(palette["muted"])
    pdf.setFont(fonts["bold"], 9)
    pdf.drawString(margin + 12 * mm, height - 47 * mm, t("Результат теста").upper())

    pdf.setFillColor(palette["ink"])
    pdf.setFont(fonts["bold"], 22)
    _draw_wrapped_text(pdf, t(result.test.title), margin + 12 * mm, height - 57 * mm, 105 * mm, fonts["bold"], 22, palette["ink"], leading=7.5 * mm, max_lines=2)

    pdf.setFillColor(palette["muted"])
    pdf.setFont(fonts["regular"], 9)
    pdf.drawString(margin + 12 * mm, height - 68 * mm, f"{t(result.test.course.title)} · {result.created_at.strftime('%d.%m.%Y %H:%M')}")

    pdf.setFillColor(palette["bg"])
    pdf.roundRect(width - margin - 42 * mm, height - 61 * mm, 34 * mm, 14 * mm, 4 * mm, stroke=0, fill=1)
    pdf.setFillColor(palette["blue"])
    pdf.setFont(fonts["bold"], 9)
    pdf.drawCentredString(width - margin - 25 * mm, height - 56 * mm, t("Код"))
    pdf.setFillColor(palette["ink"])
    pdf.setFont(fonts["bold"], 10)
    pdf.drawCentredString(width - margin - 25 * mm, height - 61 * mm, result.certificate_code)


def _draw_score_card(pdf, x, y, w, h, result, fonts, palette, status_color):
    _card(pdf, x, y - h, w, h, palette)
    cx = x + w / 2
    cy = y - 21 * mm
    pdf.setFillColor(HexColor("#e8efff"))
    pdf.circle(cx, cy, 17 * mm, stroke=0, fill=1)
    pdf.setFillColor(palette["blue"])
    pdf.circle(cx, cy, 13 * mm, stroke=0, fill=1)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.circle(cx, cy, 9 * mm, stroke=0, fill=1)
    pdf.setFillColor(palette["ink"])
    pdf.setFont(fonts["bold"], 18)
    pdf.drawCentredString(cx, cy - 2 * mm, f"{result.score:.0f}%")

    pdf.setFillColor(status_color)
    pdf.roundRect(x + 13 * mm, y - h + 7 * mm, w - 26 * mm, 8 * mm, 3 * mm, stroke=0, fill=1)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont(fonts["bold"], 8)
    pdf.drawCentredString(cx, y - h + 9.5 * mm, t("Пройден") if result.passed else t("Повторить"))


def _draw_summary_card(pdf, x, y, w, h, result, fonts, palette, status_text):
    _card(pdf, x, y - h, w, h, palette)
    rows = [
        (t("Ученик"), t(result.student.name)),
        (t("Курс"), t(result.test.course.title)),
        (t("Правильных ответов"), f"{result.correct_answers} {t('из')} {result.total_questions}"),
        (t("Статус"), status_text),
        (t("Дата"), result.created_at.strftime("%d.%m.%Y %H:%M")),
    ]
    row_y = y - 9 * mm
    for label, value in rows:
        pdf.setFillColor(palette["muted"])
        pdf.setFont(fonts["bold"], 8)
        pdf.drawString(x + 8 * mm, row_y, label)
        pdf.setFillColor(palette["ink"])
        pdf.setFont(fonts["regular"], 9)
        _draw_wrapped_text(pdf, value, x + 45 * mm, row_y, w - 53 * mm, fonts["regular"], 9, palette["ink"], leading=4.2 * mm, max_lines=1)
        row_y -= 7 * mm


def _draw_recommendation(pdf, x, y, w, recommendation, fonts, palette):
    lines = _wrap_text(pdf, recommendation.summary, w - 16 * mm, fonts["regular"], 10)
    plan_lines = []
    for line in recommendation.plan.split("\n"):
        plan_lines.extend(_wrap_text(pdf, line, w - 18 * mm, fonts["regular"], 9))
    h = 24 * mm + len(lines) * 5 * mm + len(plan_lines) * 4.6 * mm
    _card(pdf, x, y - h, w, h, palette)
    pdf.setFillColor(palette["violet"])
    pdf.roundRect(x + 7 * mm, y - 12 * mm, 28 * mm, 7 * mm, 3 * mm, stroke=0, fill=1)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont(fonts["bold"], 8)
    pdf.drawCentredString(x + 21 * mm, y - 9.5 * mm, "AI")

    pdf.setFillColor(palette["ink"])
    pdf.setFont(fonts["bold"], 14)
    pdf.drawString(x + 39 * mm, y - 10 * mm, t("Рекомендация"))

    text_y = y - 20 * mm
    for line in lines:
        pdf.setFillColor(palette["ink"])
        pdf.setFont(fonts["regular"], 10)
        pdf.drawString(x + 8 * mm, text_y, line)
        text_y -= 5 * mm

    pdf.setFillColor(palette["muted"])
    pdf.setFont(fonts["bold"], 9)
    pdf.drawString(x + 8 * mm, text_y - 1 * mm, t("План"))
    text_y -= 7 * mm

    for line in plan_lines:
        pdf.setFillColor(palette["ink"])
        pdf.setFont(fonts["regular"], 9)
        pdf.drawString(x + 10 * mm, text_y, line)
        text_y -= 4.6 * mm
    return y - h - 8 * mm


def _answer_card_height(pdf, question, selected, correct, explanation, w, fonts):
    content_w = w - 18 * mm
    count = 2
    count += len(_wrap_text(pdf, question, content_w, fonts["bold"], 11))
    count += len(_wrap_text(pdf, selected, content_w - 30 * mm, fonts["regular"], 9))
    if correct:
        count += len(_wrap_text(pdf, correct, content_w - 30 * mm, fonts["regular"], 9))
    count += len(_wrap_text(pdf, explanation, content_w, fonts["regular"], 9))
    return max(38 * mm, 14 * mm + count * 4.8 * mm)


def _draw_answer_card(pdf, x, y, w, h, index, question, selected, correct, explanation, is_correct, fonts, palette):
    _card(pdf, x, y - h, w, h, palette)
    badge_color = palette["green"] if is_correct else palette["danger"]
    pdf.setFillColor(badge_color)
    pdf.roundRect(x + 7 * mm, y - 12 * mm, 22 * mm, 7 * mm, 3 * mm, stroke=0, fill=1)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont(fonts["bold"], 8)
    pdf.drawCentredString(x + 18 * mm, y - 9.5 * mm, t("Верно") if is_correct else t("Ошибка"))

    pdf.setFillColor(palette["muted"])
    pdf.setFont(fonts["bold"], 9)
    pdf.drawRightString(x + w - 8 * mm, y - 9 * mm, f"{t('Вопрос')} {index}")

    text_y = y - 19 * mm
    text_y = _draw_wrapped_text(pdf, question, x + 8 * mm, text_y, w - 16 * mm, fonts["bold"], 11, palette["ink"], leading=5 * mm)
    text_y -= 2 * mm
    text_y = _draw_label_line(pdf, x + 8 * mm, text_y, w - 16 * mm, t("Ваш ответ:"), selected, fonts, palette)
    if correct:
        text_y = _draw_label_line(pdf, x + 8 * mm, text_y, w - 16 * mm, t("Правильный ответ:"), correct, fonts, palette)
    if explanation:
        text_y -= 1 * mm
        _draw_wrapped_text(pdf, explanation, x + 8 * mm, text_y, w - 16 * mm, fonts["regular"], 9, palette["muted"], leading=4.5 * mm)
    return y - h


def _draw_label_line(pdf, x, y, w, label, value, fonts, palette):
    pdf.setFillColor(palette["muted"])
    pdf.setFont(fonts["bold"], 9)
    pdf.drawString(x, y, label)
    label_w = pdf.stringWidth(label, fonts["bold"], 9) + 2 * mm
    return _draw_wrapped_text(pdf, value, x + label_w, y, w - label_w, fonts["regular"], 9, palette["ink"], leading=4.5 * mm)


def _draw_section_title(pdf, x, y, title, fonts, palette):
    pdf.setFillColor(palette["ink"])
    pdf.setFont(fonts["bold"], 15)
    pdf.drawString(x, y, title)
    pdf.setFillColor(palette["blue"])
    pdf.roundRect(x, y - 4 * mm, 18 * mm, 1.2 * mm, 0.5 * mm, stroke=0, fill=1)
    return y - 10 * mm


def _draw_tags(pdf, x, y, tags, w, fonts, palette):
    current_x = x
    current_y = y
    for tag in tags:
        tag_w = min(pdf.stringWidth(tag, fonts["bold"], 8) + 10 * mm, w)
        if current_x + tag_w > x + w:
            current_x = x
            current_y -= 9 * mm
        pdf.setFillColor(HexColor("#e8efff"))
        pdf.roundRect(current_x, current_y - 5 * mm, tag_w, 7 * mm, 3 * mm, stroke=0, fill=1)
        pdf.setFillColor(palette["blue"])
        pdf.setFont(fonts["bold"], 8)
        pdf.drawString(current_x + 4 * mm, current_y - 2.5 * mm, tag)
        current_x += tag_w + 3 * mm
    return current_y - 8 * mm


def _card(pdf, x, y, w, h, palette):
    pdf.setFillColor(HexColor("#d8e0ec"))
    pdf.roundRect(x + 0.8 * mm, y - 0.8 * mm, w, h, 5 * mm, stroke=0, fill=1)
    pdf.setFillColor(palette["surface"])
    pdf.roundRect(x, y, w, h, 5 * mm, stroke=0, fill=1)
    pdf.setStrokeColor(palette["line"])
    pdf.setLineWidth(0.6)
    pdf.roundRect(x, y, w, h, 5 * mm, stroke=1, fill=0)


def _draw_logo(pdf, x, y, size, palette):
    pdf.saveState()
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.roundRect(x, y, size, size, 3 * mm, stroke=0, fill=1)
    pdf.setStrokeColor(palette["blue"])
    pdf.setLineWidth(1.2)
    pdf.roundRect(x, y, size, size, 3 * mm, stroke=1, fill=0)

    cx = x + size / 2
    top = y + size * 0.73
    pdf.setFillColor(palette["blue"])
    path = pdf.beginPath()
    path.moveTo(cx, top)
    path.lineTo(x + size * 0.18, y + size * 0.55)
    path.lineTo(cx, y + size * 0.38)
    path.lineTo(x + size * 0.82, y + size * 0.55)
    path.close()
    pdf.drawPath(path, stroke=0, fill=1)

    pdf.setStrokeColor(palette["sky"])
    pdf.setLineWidth(1.4)
    pdf.line(x + size * 0.24, y + size * 0.29, cx, y + size * 0.43)
    pdf.line(x + size * 0.76, y + size * 0.29, cx, y + size * 0.43)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.circle(cx, y + size * 0.25, size * 0.13, stroke=1, fill=1)
    pdf.setStrokeColor(palette["violet"])
    pdf.setLineWidth(1.4)
    pdf.line(cx - size * 0.07, y + size * 0.25, cx - size * 0.02, y + size * 0.2)
    pdf.line(cx - size * 0.02, y + size * 0.2, cx + size * 0.08, y + size * 0.31)
    pdf.restoreState()


def _draw_wrapped_text(pdf, text, x, y, w, font, size, color, leading=None, max_lines=None):
    leading = leading or size * 1.35
    lines = _wrap_text(pdf, text, w, font, size)
    if max_lines:
        lines = lines[:max_lines]
    pdf.setFillColor(color)
    pdf.setFont(font, size)
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _wrap_text(pdf, text, w, font, size):
    words = str(text or "").replace("\r\n", "\n").split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if pdf.stringWidth(candidate, font, size) <= w:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _register_fonts(pdfmetrics, TTFont):
    regular_candidates = [
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    bold_candidates = [
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    regular = _register_first_font(pdfmetrics, TTFont, "AppFont", regular_candidates)
    bold = _register_first_font(pdfmetrics, TTFont, "AppFontBold", bold_candidates) or regular
    return {"regular": regular or "Helvetica", "bold": bold or "Helvetica-Bold"}


def _register_first_font(pdfmetrics, TTFont, name, candidates):
    for path in candidates:
        if path.exists():
            pdfmetrics.registerFont(TTFont(name, str(path)))
            return name
    return None
