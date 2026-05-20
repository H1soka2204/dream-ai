import json
import re
from collections import Counter

import requests
from flask import current_app

from services.i18n import current_language, t


def _english():
    return current_language() == "en"


def generate_questions(topic, count=5, difficulty="middle"):
    if _english():
        prompt = (
            "Create a JSON array of test questions in English. "
            "Each object must contain: text, topic, explanation, answers. "
            "answers must contain 4 objects with text and is_correct. "
            f"Topic: {topic}. Count: {count}. Difficulty: {difficulty}."
        )
    else:
        prompt = (
            "Создай JSON-массив вопросов для теста. "
            "Формат каждого объекта: text, topic, explanation, answers. "
            "answers содержит 4 объекта text и is_correct. "
            f"Тема: {topic}. Количество: {count}. Сложность: {difficulty}."
        )
    data = _call_ai(prompt)
    parsed = _extract_json(data)
    if isinstance(parsed, list) and parsed:
        return parsed[: int(count)]
    return _fallback_questions(topic, int(count), difficulty)


def generate_recommendation(user, result, wrong_items):
    weak_topics = [item["topic"] for item in wrong_items]
    weak_counter = Counter(weak_topics)
    weak_text = ", ".join([t(topic) for topic, _ in weak_counter.most_common()]) or t("нет")
    if _english():
        prompt = (
            "You are an AI mentor for an education platform. "
            "Create a short analysis of the test result, weak topics, and a 5-step learning plan in English. "
            "Return a JSON object with fields: summary, weak_topics, plan. "
            f"Student: {t(user.name)}. Test: {t(result.test.title)}. "
            f"Score: {result.score:.0f}%. Weak topics: {weak_text}."
        )
    else:
        prompt = (
            "Ты AI-наставник образовательной платформы. "
            "Сформируй краткий анализ результата теста, слабые темы и план обучения на 5 шагов. "
            "Ответ верни JSON-объектом с полями summary, weak_topics, plan. "
            f"Ученик: {user.name}. Тест: {result.test.title}. "
            f"Результат: {result.score:.0f}%. Слабые темы: {weak_text}."
        )
    data = _call_ai(prompt)
    parsed = _extract_json(data)
    if isinstance(parsed, dict) and parsed.get("summary") and parsed.get("plan"):
        return {
            "summary": _recommendation_text(parsed.get("summary")),
            "weak_topics": _recommendation_text(parsed.get("weak_topics", weak_text)),
            "plan": _recommendation_text(parsed.get("plan")),
        }
    return _fallback_recommendation(result, weak_counter)


def _recommendation_text(value):
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return "\n".join(
            f"{key}: {item}" for key, item in value.items() if str(item).strip()
        )
    return str(value).strip()


def chat_with_gemini(message, history=None, user=None):
    message = (message or "").strip()
    if not message:
        return {
            "reply": t("Напишите вопрос, и Gemini AI поможет с учебной темой."),
            "provider": "fallback",
            "model": "local",
        }

    model = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
    if current_app.config.get("AI_PROVIDER") == "gemini" and current_app.config.get("GEMINI_API_KEY"):
        reply, error = _call_gemini_chat(message, history or [], user)
        if reply:
            return {"reply": _clean_ai_text(reply), "provider": "gemini", "model": model}
        return {
            "reply": _fallback_chat_reply(message, gemini_error=error),
            "provider": "fallback",
            "model": "local",
            "gemini_error": error,
        }

    return {
        "reply": _fallback_chat_reply(message),
        "provider": "fallback",
        "model": "local",
    }


def _call_ai(prompt):
    provider = current_app.config.get("AI_PROVIDER", "fallback")
    if provider == "openai" and current_app.config.get("OPENAI_API_KEY"):
        return _call_openai(prompt)
    if provider == "gemini" and current_app.config.get("GEMINI_API_KEY"):
        return _call_gemini(prompt)
    return None


def _call_openai(prompt):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {current_app.config['OPENAI_API_KEY']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": current_app.config.get("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": t("Отвечай только валидным JSON без Markdown.")},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def _call_gemini(prompt):
    model = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
    key = current_app.config["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": t("Отвечай только валидным JSON без Markdown.") + "\n" + prompt}
                ]
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def _call_gemini_chat(message, history, user):
    model = current_app.config.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
    key = current_app.config["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key,
    }
    contents = _gemini_chat_contents(message, history, user)
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "maxOutputTokens": 1200,
        },
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        response.raise_for_status()
        return _extract_gemini_text(response.json()), None
    except requests.RequestException as error:
        return None, _gemini_request_error(error)
    except Exception:
        return None, "не удалось разобрать ответ Gemini API"


def _gemini_request_error(error):
    response = getattr(error, "response", None)
    if response is None:
        return "нет ответа от Gemini API"
    try:
        data = response.json()
    except ValueError:
        return f"Gemini API вернул HTTP {response.status_code}"
    details = data.get("error", {})
    status = details.get("status")
    code = details.get("code", response.status_code)
    if code == 429 or status == "RESOURCE_EXHAUSTED":
        return "квота Gemini API исчерпана или недоступна для выбранной модели"
    if code in {401, 403}:
        return "ключ Gemini API отклонен или не имеет доступа"
    message = str(details.get("message", "")).strip()
    if message:
        return f"Gemini API вернул HTTP {code}: {message[:220]}"
    return f"Gemini API вернул HTTP {code}"


def _gemini_chat_contents(message, history, user):
    if _english():
        system_prompt = (
            "Return plain text only. Do not use Markdown symbols such as ###, **, *, tables, pipes or code fences. "
            "You are the Gemini AI chat for the AI Edu Test education platform. "
            "Answer in English clearly, kindly, and directly. "
            "Help with learning topics, test mistakes, review plans, Python, Flask, AI, and web development. "
            "If the user asks for a finished homework answer, first explain the reasoning and give hints. "
            "Do not invent facts: if information is missing, ask a short clarifying question."
        )
    else:
        system_prompt = (
            "Return plain text only. Do not use Markdown symbols such as ###, **, *, tables, pipes or code fences. "
            "Ты Gemini AI-чат образовательной платформы AI Edu Test. "
            "Отвечай на русском языке ясно, дружелюбно и по делу. "
            "Помогай разбирать учебные темы, ошибки в тестах, планы повторения, Python, Flask, AI и веб-разработку. "
            "Если пользователь просит готовый ответ на учебное задание, сначала объясни ход решения и дай подсказки. "
            "Не выдумывай факты: если данных не хватает, коротко уточни вопрос."
        )
    context = _user_context_text(user)
    contents = [
        {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{t('Контекст пользователя')}: {context}"}]},
        {"role": "model", "parts": [{"text": t("Понял. Я буду отвечать как учебный AI-помощник.")}]},
    ]
    for item in _normalize_chat_history(history):
        role = "model" if item["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": item["content"]}]})
    contents.append({"role": "user", "parts": [{"text": message[:4000]}]})
    return contents


def _normalize_chat_history(history):
    if not isinstance(history, list):
        return []
    normalized = []
    for item in history[-12:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            normalized.append({"role": role, "content": content[:2000]})
    return normalized


def _user_context_text(user):
    if not user or not getattr(user, "is_authenticated", False):
        return t("гость")
    role_label = {
        "student": t("ученик"),
        "teacher": t("преподаватель"),
        "admin": t("администратор"),
    }.get(getattr(user, "role", ""), t("пользователь"))
    return f"{t(getattr(user, 'name', 'пользователь'))}, {t('роль')}: {role_label}"


def _extract_gemini_text(data):
    candidates = data.get("candidates") or []
    if not candidates:
        return None
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()
    return text or None


def _clean_ai_text(text):
    cleaned_lines = []
    for line in str(text or "").replace("\r\n", "\n").split("\n"):
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", line.rstrip())
        cleaned = re.sub(r"^\s*[*+]\s+", "- ", cleaned)
        cleaned = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", cleaned)
        cleaned = re.sub(r"__([^_\n]+)__", r"\1", cleaned)
        cleaned = re.sub(r"\*([^*\n]+)\*", r"\1", cleaned)
        cleaned = re.sub(r"_([^_\n]+)_", r"\1", cleaned)
        cleaned = re.sub(r"`([^`\n]+)`", r"\1", cleaned)
        cleaned = cleaned.replace("|", "")
        cleaned = re.sub(r"\s+([,.!?;:])", r"\1", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned_lines.append(cleaned)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned_lines)).strip()


def _extract_json(raw_text):
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json\n", "", 1).replace("JSON\n", "", 1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = min([i for i in [cleaned.find("["), cleaned.find("{")] if i != -1], default=-1)
        end = max(cleaned.rfind("]"), cleaned.rfind("}"))
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _fallback_chat_reply(message, gemini_error=None):
    lowered = message.lower()
    if _english():
        if gemini_error:
            setup_note = f"Gemini AI is configured but currently unavailable: {gemini_error}. I am answering locally for now."
        else:
            setup_note = (
                "Gemini AI is not connected yet. Set `AI_PROVIDER=gemini` and add `GEMINI_API_KEY` in `.env` "
                "so the chat can answer through Gemini."
            )
        if any(word in lowered for word in ["python", "function", "list", "tuple"]):
            return (
                f"{setup_note}\n\n"
                "Local answer: start by naming the topic, review an example, and check yourself with a short test. "
                "For Python, write down the inputs, expected output, and only then write the code."
            )
        if any(word in lowered for word in ["test", "mistake", "score", "result", "error"]):
            return (
                f"{setup_note}\n\n"
                "Local answer: list the questions you missed, group them by topic, and review the most frequent topic first. "
                "Then complete 5-10 similar tasks without hints."
            )
        if any(word in lowered for word in ["plan", "learn", "review", "prepare", "study"]):
            return (
                f"{setup_note}\n\n"
                "Local answer: 1) review theory, 2) solve several short tasks, 3) analyze mistakes, "
                "4) repeat tomorrow, 5) check progress with a test."
            )
        return (
            f"{setup_note}\n\n"
            "Local answer: clarify the topic, your goal, and what you have already tried. "
            "That will make the explanation more useful once Gemini is connected."
        )
    if gemini_error:
        setup_note = f"Gemini AI настроен, но сейчас недоступен: {gemini_error}. Временно отвечаю локально."
    else:
        setup_note = (
            "Gemini AI сейчас не подключен. Включите `AI_PROVIDER=gemini` и добавьте `GEMINI_API_KEY` в `.env`, "
            "чтобы чат отвечал через Gemini."
        )
    if any(word in lowered for word in ["python", "питон", "функц", "спис", "кортеж"]):
        return (
            f"{setup_note}\n\n"
            "Пока доступен локальный ответ: начните с формулировки темы, затем разберите пример и проверьте себя коротким тестом. "
            "Для Python полезно выписать входные данные, ожидаемый результат и только потом писать код."
        )
    if any(word in lowered for word in ["тест", "ошиб", "балл", "результат"]):
        return (
            f"{setup_note}\n\n"
            "Пока доступен локальный ответ: выпишите вопросы с ошибками, сгруппируйте их по темам и повторите самую частую тему первой. "
            "После этого пройдите 5-10 похожих заданий без подсказок."
        )
    if any(word in lowered for word in ["план", "учить", "повтор", "подготов"]):
        return (
            f"{setup_note}\n\n"
            "Пока доступен локальный ответ: 1) повторите теорию, 2) решите несколько коротких задач, "
            "3) разберите ошибки, 4) повторите через день, 5) проверьте прогресс тестом."
        )
    return (
        f"{setup_note}\n\n"
        "Пока доступен локальный ответ: уточните тему, цель и что уже пробовали. "
        "Так можно быстрее получить полезное объяснение после подключения Gemini."
    )


def _fallback_questions(topic, count, difficulty):
    questions = []
    if _english():
        templates = [
            (
                f"What best describes the key idea of “{topic}”?",
                "Understanding the main principles and applying them in practice.",
            ),
            (
                f"Which step helps reinforce knowledge of “{topic}”?",
                "Practice with feedback and mistake review.",
            ),
            (
                f"What is important to check after studying “{topic}”?",
                "The ability to explain the solution and find weak spots.",
            ),
            (
                f"How can AI help when learning “{topic}”?",
                "By selecting tasks, explanations, and a personal review plan.",
            ),
            (
                f"Which indicator best shows progress in “{topic}”?",
                "A higher percentage of correct answers and fewer repeated mistakes.",
            ),
        ]
        explanation = "The correct answer is connected to practical understanding, not mechanical memorization."
        wrong_answers = [
            "Choosing an answer randomly without analysis.",
            "Ignoring mistakes after the test.",
            "Studying without review or practice.",
        ]
    else:
        templates = [
            (
                f"Что лучше всего описывает ключевую идею темы «{topic}»?",
                "Понимание основных принципов и умение применять их на практике.",
            ),
            (
                f"Какой шаг помогает закрепить знания по теме «{topic}»?",
                "Практика с обратной связью и разбором ошибок.",
            ),
            (
                f"Что важно проверить после изучения темы «{topic}»?",
                "Умение объяснить решение и найти слабые места.",
            ),
            (
                f"Как AI может помочь при изучении темы «{topic}»?",
                "Подобрать задания, объяснения и индивидуальный план повторения.",
            ),
            (
                f"Какой показатель лучше всего показывает прогресс по теме «{topic}»?",
                "Рост процента правильных ответов и снижение повторяющихся ошибок.",
            ),
        ]
        explanation = "Правильный ответ связан с практическим пониманием темы, а не с механическим запоминанием."
        wrong_answers = [
            "Случайный выбор ответа без анализа.",
            "Игнорирование ошибок после теста.",
            "Изучение без повторения и практики.",
        ]
    for index in range(count):
        text, correct = templates[index % len(templates)]
        questions.append(
            {
                "text": text,
                "topic": topic,
                "difficulty": difficulty,
                "explanation": explanation,
                "answers": [
                    {"text": correct, "is_correct": True},
                    {"text": wrong_answers[0], "is_correct": False},
                    {"text": wrong_answers[1], "is_correct": False},
                    {"text": wrong_answers[2], "is_correct": False},
                ],
            }
        )
    return questions


def _fallback_recommendation(result, weak_counter):
    test_title = t(result.test.title)
    if weak_counter:
        weak_topics = ", ".join([t(topic) for topic, _ in weak_counter.most_common()])
        focus = t(weak_counter.most_common(1)[0][0])
        if _english():
            summary = (
                f"Your score on “{test_title}” is {result.score:.0f}%. "
                f"Main growth area: {focus}."
            )
        else:
            summary = (
                f"Ваш результат по тесту «{result.test.title}» — {result.score:.0f}%. "
                f"Главная зона роста: {focus}."
            )
    else:
        weak_topics = t("нет выраженных слабых тем")
        if _english():
            summary = (
                f"Great work: your score on “{test_title}” is "
                f"{result.score:.0f}%. You can move on to more advanced tasks."
            )
        else:
            summary = (
                f"Отличная работа: результат по тесту «{result.test.title}» — "
                f"{result.score:.0f}%. Можно переходить к более сложным заданиям."
            )
    if _english():
        plan = "\n".join(
            [
                "1. Review theory for weak topics and write down key rules.",
                "2. Analyze every wrong answer and define the reason for the mistake.",
                "3. Complete 10 short practice tasks on the selected topic.",
                "4. Retake the test with a timer tomorrow.",
                "5. If the score is above 85%, move to the next difficulty level.",
            ]
        )
    else:
        plan = "\n".join(
            [
                "1. Повторите теорию по слабым темам и выпишите ключевые правила.",
                "2. Разберите каждый неправильный ответ и сформулируйте причину ошибки.",
                "3. Пройдите 10 коротких практических заданий по выбранной теме.",
                "4. Через день повторите тест с таймером.",
                "5. Если результат выше 85%, переходите к следующему уровню сложности.",
            ]
        )
    return {"summary": summary, "weak_topics": weak_topics, "plan": plan}
