(function () {
    const root = document.documentElement;
    const storedTheme = safeStorageGet("theme");
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = root.dataset.theme || storedTheme || (prefersDark ? "dark" : "light");

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
            safeStorageSet("theme", root.dataset.theme);
            drawAllCharts();
        });
    });

    const navToggle = document.querySelector("[data-nav-toggle]");
    const nav = document.querySelector("[data-nav]");
    if (navToggle && nav) {
        navToggle.addEventListener("click", () => nav.classList.toggle("is-open"));
    }

    document.querySelectorAll(".flash").forEach((flash) => {
        window.setTimeout(() => {
            flash.style.opacity = "0";
            flash.style.transform = "translateY(-8px)";
        }, 4500);
    });

    setupHeroCanvas();
    setupTimer();
    setupAnswers();
    setupGeminiChat();
    drawAllCharts();
    window.addEventListener("resize", drawAllCharts);
    if (document.fonts) {
        document.fonts.ready.then(drawAllCharts);
    }
})();

function safeStorageGet(key) {
    try {
        return localStorage.getItem(key);
    } catch (_error) {
        return null;
    }
}

function safeStorageSet(key, value) {
    try {
        localStorage.setItem(key, value);
    } catch (_error) {
        return null;
    }
    return value;
}

function uiText(ru, en) {
    return document.documentElement.lang === "en" ? en : ru;
}

function setupHeroCanvas() {
    const canvas = document.getElementById("hero-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    let width = 0;
    let height = 0;
    let points = [];

    function resize() {
        const rect = canvas.getBoundingClientRect();
        width = canvas.width = Math.floor(rect.width * window.devicePixelRatio);
        height = canvas.height = Math.floor(rect.height * window.devicePixelRatio);
        ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
        const count = Math.max(36, Math.floor(rect.width / 26));
        points = Array.from({ length: count }, () => ({
            x: Math.random() * rect.width,
            y: Math.random() * rect.height,
            vx: (Math.random() - 0.5) * 0.35,
            vy: (Math.random() - 0.5) * 0.35,
            r: 1.5 + Math.random() * 2.5,
        }));
    }

    function frame() {
        const rect = canvas.getBoundingClientRect();
        ctx.clearRect(0, 0, rect.width, rect.height);
        points.forEach((point) => {
            point.x += point.vx;
            point.y += point.vy;
            if (point.x < 0 || point.x > rect.width) point.vx *= -1;
            if (point.y < 0 || point.y > rect.height) point.vy *= -1;
        });

        for (let i = 0; i < points.length; i += 1) {
            for (let j = i + 1; j < points.length; j += 1) {
                const a = points[i];
                const b = points[j];
                const dx = a.x - b.x;
                const dy = a.y - b.y;
                const distance = Math.sqrt(dx * dx + dy * dy);
                if (distance < 145) {
                    ctx.strokeStyle = `rgba(96, 165, 250, ${0.22 - distance / 700})`;
                    ctx.lineWidth = 1;
                    ctx.beginPath();
                    ctx.moveTo(a.x, a.y);
                    ctx.lineTo(b.x, b.y);
                    ctx.stroke();
                }
            }
        }

        points.forEach((point, index) => {
            ctx.fillStyle = index % 4 === 0 ? "#2dd4bf" : index % 3 === 0 ? "#a78bfa" : "#60a5fa";
            ctx.beginPath();
            ctx.arc(point.x, point.y, point.r, 0, Math.PI * 2);
            ctx.fill();
        });
        requestAnimationFrame(frame);
    }

    resize();
    window.addEventListener("resize", resize);
    frame();
}

function setupTimer() {
    const timer = document.querySelector("[data-timer]");
    const form = document.querySelector("[data-test-form]");
    const hidden = document.querySelector("[data-time-spent]");
    if (!timer || !form || !hidden) return;

    const totalSeconds = Math.max(1, Number(timer.dataset.minutes || 1) * 60);
    let remaining = totalSeconds;
    let elapsed = 0;
    const minutesNode = document.querySelector("[data-timer-minutes]");
    const secondsNode = document.querySelector("[data-timer-seconds]");

    function render() {
        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;
        minutesNode.textContent = String(minutes).padStart(2, "0");
        secondsNode.textContent = String(seconds).padStart(2, "0");
        hidden.value = String(elapsed);
        timer.classList.toggle("danger", remaining <= 60);
    }

    const interval = window.setInterval(() => {
        remaining -= 1;
        elapsed += 1;
        render();
        if (remaining <= 0) {
            window.clearInterval(interval);
            form.requestSubmit();
        }
    }, 1000);

    form.addEventListener("submit", () => {
        hidden.value = String(elapsed);
    });
    render();
}

function setupAnswers() {
    document.querySelectorAll(".answer-option input").forEach((input) => {
        input.addEventListener("change", () => {
            const group = document.querySelectorAll(`input[name="${input.name}"]`);
            group.forEach((item) => item.closest(".answer-option").classList.remove("is-selected"));
            input.closest(".answer-option").classList.add("is-selected");
        });
    });
}

function setupGeminiChat() {
    const chat = document.querySelector("[data-ai-chat]");
    if (!chat) return;

    const form = chat.querySelector("[data-chat-form]");
    const input = chat.querySelector("[data-chat-input]");
    const messagesNode = chat.querySelector("[data-chat-messages]");
    const providerNode = document.querySelector("[data-chat-provider]");
    const endpoint = chat.dataset.endpoint;
    const initialPrompt = (chat.dataset.initialPrompt || "").trim();
    const history = [];

    document.querySelectorAll("[data-chat-suggestion]").forEach((button) => {
        button.addEventListener("click", () => {
            input.value = button.dataset.chatSuggestion || "";
            input.focus();
        });
    });

    const sendChatMessage = async (message) => {
        message = String(message || "").trim();
        if (!message) return;

        const priorHistory = history.slice(-12);
        appendChatMessage(messagesNode, "user", message);
        history.push({ role: "user", content: message });
        input.value = "";

        const pending = appendChatMessage(messagesNode, "assistant", uiText("Gemini думает...", "Gemini is thinking..."), "pending");
        setChatLoading(form, true);

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ message, history: priorHistory }),
            });
            const isJson = response.headers.get("content-type")?.includes("application/json");
            const data = isJson ? await response.json() : {};
            if (!response.ok) {
                throw new Error(data.error || uiText("Не удалось получить ответ.", "Could not get a response."));
            }

            const reply = data.reply || uiText("Gemini вернул пустой ответ.", "Gemini returned an empty response.");
            const formattedReply = formatAssistantText(reply);
            updateChatMessage(pending, formattedReply);
            pending.classList.remove("pending");
            history.push({ role: "assistant", content: formattedReply });
            updateChatProvider(providerNode, data.provider, data.model);
        } catch (_error) {
            updateChatMessage(pending, uiText("Не удалось получить ответ. Проверьте подключение Gemini и попробуйте еще раз.", "Could not get a response. Check the Gemini connection and try again."));
            pending.classList.remove("pending");
        } finally {
            setChatLoading(form, false);
            input.focus();
        }
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        await sendChatMessage(input.value);
    });

    if (initialPrompt) {
        window.setTimeout(() => {
            sendChatMessage(initialPrompt);
        }, 250);
    }
}

function appendChatMessage(messagesNode, role, text, extraClass = "") {
    const message = document.createElement("div");
    message.className = `chat-message ${role}${extraClass ? ` ${extraClass}` : ""}`;
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble";
    bubble.textContent = text;
    message.appendChild(bubble);
    messagesNode.appendChild(message);
    messagesNode.scrollTop = messagesNode.scrollHeight;
    return message;
}

function updateChatMessage(message, text) {
    const bubble = message.querySelector(".chat-bubble");
    if (bubble) bubble.textContent = text;
    const messagesNode = message.parentElement;
    if (messagesNode) messagesNode.scrollTop = messagesNode.scrollHeight;
}

function formatAssistantText(text) {
    return String(text || "")
        .replace(/\r\n/g, "\n")
        .replace(/```[a-zA-Z0-9_-]*\n?/g, "")
        .replace(/```/g, "")
        .split("\n")
        .map((line) => {
            let cleaned = line.trimEnd();
            cleaned = cleaned.replace(/^\s{0,3}#{1,6}\s*/, "");
            cleaned = cleaned.replace(/^\s*[*+]\s+/, "- ");
            cleaned = cleaned.replace(/\*\*([^*\n]+)\*\*/g, "$1");
            cleaned = cleaned.replace(/__([^_\n]+)__/g, "$1");
            cleaned = cleaned.replace(/\*([^*\n]+)\*/g, "$1");
            cleaned = cleaned.replace(/_([^_\n]+)_/g, "$1");
            cleaned = cleaned.replace(/`([^`\n]+)`/g, "$1");
            cleaned = cleaned.replace(/\|/g, "");
            cleaned = cleaned.replace(/\s+([,.!?;:])/g, "$1");
            cleaned = cleaned.replace(/[ \t]{2,}/g, " ");
            return cleaned;
        })
        .join("\n")
        .replace(/\n{3,}/g, "\n\n")
        .trim();
}

function setChatLoading(form, isLoading) {
    form.querySelectorAll("button, textarea").forEach((node) => {
        node.disabled = isLoading;
    });
}

function updateChatProvider(providerNode, provider, model) {
    if (!providerNode) return;
    const isGemini = provider === "gemini";
    providerNode.textContent = isGemini ? `Gemini · ${model || ""}` : "Fallback";
    providerNode.classList.toggle("ok", isGemini);
    providerNode.classList.toggle("warn", !isGemini);
}

function drawAllCharts() {
    document.querySelectorAll(".line-chart").forEach(drawLineChart);
    document.querySelectorAll(".bar-chart").forEach(drawBarChart);
}

function parseChartData(canvas) {
    try {
        return JSON.parse(canvas.dataset.chart || "[]");
    } catch (_error) {
        return [];
    }
}

function chartColors() {
    const style = getComputedStyle(document.documentElement);
    return {
        text: style.getPropertyValue("--text").trim(),
        muted: style.getPropertyValue("--muted").trim(),
        line: style.getPropertyValue("--line").trim(),
        primary: style.getPropertyValue("--primary").trim(),
        teal: style.getPropertyValue("--teal").trim(),
        violet: style.getPropertyValue("--violet").trim(),
    };
}

function chartFont(size = 12, weight = 600) {
    const family = getComputedStyle(document.documentElement).getPropertyValue("--font-sans").trim();
    return `${weight} ${size}px ${family || '"Segoe UI", Arial, sans-serif'}`;
}

function prepareCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.floor(rect.width * ratio));
    canvas.height = Math.max(1, Math.floor(rect.height * ratio));
    const ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    return { ctx, width: rect.width, height: rect.height };
}

function drawLineChart(canvas) {
    const data = parseChartData(canvas);
    const { ctx, width, height } = prepareCanvas(canvas);
    const colors = chartColors();
    const pad = 34;
    ctx.clearRect(0, 0, width, height);
    ctx.font = chartFont(12, 600);

    drawGrid(ctx, width, height, pad, colors);
    if (!data.length) {
        ctx.fillStyle = colors.muted;
        ctx.fillText(uiText("Данные появятся после тестирования", "Data will appear after testing"), pad, height / 2);
        return;
    }

    const max = 100;
    const step = data.length > 1 ? (width - pad * 2) / (data.length - 1) : 0;
    const points = data.map((item, index) => ({
        x: pad + step * index,
        y: height - pad - (Number(item.value) / max) * (height - pad * 2),
        label: item.label,
        value: item.value,
    }));

    ctx.strokeStyle = colors.primary;
    ctx.lineWidth = 3;
    ctx.beginPath();
    points.forEach((point, index) => {
        if (index === 0) ctx.moveTo(point.x, point.y);
        else ctx.lineTo(point.x, point.y);
    });
    ctx.stroke();

    points.forEach((point) => {
        ctx.fillStyle = colors.primary;
        ctx.beginPath();
        ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = colors.muted;
        ctx.fillText(point.label, point.x - 14, height - 8);
        ctx.fillStyle = colors.text;
        ctx.fillText(`${point.value}%`, point.x - 16, point.y - 12);
    });
}

function drawBarChart(canvas) {
    const data = parseChartData(canvas);
    const { ctx, width, height } = prepareCanvas(canvas);
    const colors = chartColors();
    const pad = 34;
    ctx.clearRect(0, 0, width, height);
    ctx.font = chartFont(12, 600);
    drawGrid(ctx, width, height, pad, colors);

    if (!data.length) return;
    const max = Math.max(...data.map((item) => Number(item.value)), 1);
    const barWidth = Math.max(34, (width - pad * 2) / data.length - 18);

    data.forEach((item, index) => {
        const x = pad + index * ((width - pad * 2) / data.length) + 9;
        const barHeight = (Number(item.value) / max) * (height - pad * 2);
        const y = height - pad - barHeight;
        ctx.fillStyle = index % 2 ? colors.violet : colors.teal;
        roundedRect(ctx, x, y, barWidth, barHeight, 6);
        ctx.fill();
        ctx.fillStyle = colors.text;
        ctx.fillText(String(item.value), x + barWidth / 2 - 4, y - 8);
        ctx.fillStyle = colors.muted;
        ctx.fillText(item.label, x, height - 8);
    });
}

function drawGrid(ctx, width, height, pad, colors) {
    ctx.strokeStyle = colors.line;
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i += 1) {
        const y = pad + ((height - pad * 2) / 4) * i;
        ctx.beginPath();
        ctx.moveTo(pad, y);
        ctx.lineTo(width - pad, y);
        ctx.stroke();
    }
}

function roundedRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
}
