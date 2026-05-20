# AI Edu Test

Современная образовательная платформа на Flask: курсы, учебные материалы, тестирование, автоматическая проверка, история результатов, PDF-экспорт и AI-рекомендации через Gemini/OpenAI или локальный fallback.

## Возможности

- Регистрация и авторизация пользователей.
- Роли: ученик, преподаватель, администратор.
- Каталог курсов с поиском и фильтрами.
- Учебные материалы, тесты, вопросы и варианты ответов.
- Таймер тестирования, автоматическая проверка и расчет процента.
- Анализ ошибок, слабые темы, история тестов и прогресс.
- AI-рекомендации и генерация вопросов.
- Кабинет преподавателя для создания курсов, уроков и тестов.
- Админ-панель для управления пользователями и курсами.
- Интерактивные графики без внешних JS-зависимостей.
- Светлая и темная тема, адаптивный UI.

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Для macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Настройка AI API

Скопируйте пример окружения:

```bash
copy .env.example .env
```

Для macOS/Linux:

```bash
cp .env.example .env
```

Режим без внешнего API:

```env
AI_PROVIDER=fallback
```

Gemini:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.0-flash-lite
```

OpenAI:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4o-mini
```

Если ключ не указан или API недоступен, система автоматически использует локальный fallback для вопросов и рекомендаций.

## Запуск

```bash
python main.py
```

Откройте в браузере:

```text
http://127.0.0.1:5000
```

SQLite-база создается автоматически в `database/app.db`. При первом запуске добавляются демо-данные.

## Демо-аккаунты

```text
Ученик:        student@ai.edu / student123
Преподаватель: teacher@ai.edu / teacher123
Администратор: admin@ai.edu / admin123
```

## Как пользоваться

1. Войдите как ученик и откройте каталог курсов.
2. Выберите курс, изучите материалы и запустите тест.
3. После отправки система покажет процент, ошибки, слабые темы и AI-рекомендацию.
4. В кабинете ученика доступна история тестов, прогресс и PDF-экспорт результата.
5. Войдите как преподаватель, чтобы добавлять курсы, материалы и генерировать тесты.
6. Войдите как администратор, чтобы менять роли, отключать пользователей и управлять статусом курсов.

## API

Основные endpoints:

```text
GET  /api/courses
GET  /api/courses/<id>
GET  /api/tests/<id>
POST /api/tests/<id>/submit
GET  /api/results
GET  /api/recommendations/<result_id>
POST /api/ai/questions
GET  /api/users
GET  /api/stats/overview
```

## Публикация без домена

Проект подготовлен для Render. После публикации репозитория на GitHub можно создать Web Service на Render и использовать:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn main:app
```

Также в проекте есть `render.yaml`, поэтому Render может взять настройки автоматически. После успешного деплоя приложение будет доступно по адресу вида:

```text
https://dream-ai.onrender.com
```

Свой домен для этого не нужен.

## Структура проекта

```text
.
├── ai/
│   └── providers.py
├── backend/
│   ├── __init__.py
│   └── config.py
├── database/
├── frontend/
├── models/
│   └── entities.py
├── routes/
│   ├── admin.py
│   ├── api.py
│   ├── auth.py
│   ├── main.py
│   ├── student.py
│   └── teacher.py
├── services/
│   ├── ai_service.py
│   ├── authz.py
│   ├── pdf_service.py
│   ├── seed.py
│   ├── stats_service.py
│   └── test_service.py
├── static/
│   ├── css/
│   │   └── styles.css
│   ├── images/
│   └── js/
│       └── app.js
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── errors/
│   ├── student/
│   ├── teacher/
│   ├── base.html
│   ├── course_detail.html
│   ├── courses.html
│   ├── index.html
│   └── stats.html
├── .env.example
├── main.py
├── README.md
└── requirements.txt
```
