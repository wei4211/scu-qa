const form = document.getElementById("question-form");
const input = document.getElementById("question");
const messages = document.getElementById("messages");
const send = document.getElementById("send-button");
const examples = document.querySelectorAll(".examples button");
const chat = document.querySelector(".chat");
const history = [];
const stopVoice = connectVoice(
  input, document.getElementById("voice-status"), document.getElementById("voice-button"),
  chat.dataset.voiceEnabled === "true",
);

const assistantAvatar = document.getElementById("assistant-avatar").content;

// A soft light that follows the mouse across the background (mouse and trackpad only).
const glow = document.querySelector(".cursor-glow");
if (glow && matchMedia("(hover: hover) and (pointer: fine)").matches) {
  const target = { x: innerWidth / 2, y: innerHeight / 3 };
  const current = { ...target };
  const ease = matchMedia("(prefers-reduced-motion: reduce)").matches ? 1 : .14;
  let frame = 0;
  const render = () => {
    current.x += (target.x - current.x) * ease;
    current.y += (target.y - current.y) * ease;
    glow.style.setProperty("--mx", `${current.x}px`);
    glow.style.setProperty("--my", `${current.y}px`);
    frame = Math.abs(target.x - current.x) + Math.abs(target.y - current.y) > .5 ? requestAnimationFrame(render) : 0;
  };
  addEventListener("pointermove", event => {
    // The desktop page is CSS-zoomed (see --ui-zoom), so convert window pixels into page pixels.
    const zoom = parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
    target.x = event.clientX / zoom;
    target.y = event.clientY / zoom;
    glow.classList.add("is-active");
    if (!frame) frame = requestAnimationFrame(render);
  }, { passive: true });
  document.documentElement.addEventListener("pointerleave", () => glow.classList.remove("is-active"));
}

// Let the side robots take turns saying a short line.
const bubbles = document.querySelectorAll(".bot-bubble[data-phrases]");
if (bubbles.length && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
  bubbles.forEach((bubble, index) => {
    const phrases = bubble.dataset.phrases.split("|");
    const text = bubble.querySelector("span");
    let current = 0;
    setTimeout(() => setInterval(() => {
      text.classList.add("is-leaving");
      setTimeout(() => {
        current = (current + 1) % phrases.length;
        text.textContent = phrases[current];
        text.classList.remove("is-leaving");
      }, 350);
    }, 4200), index * 2100);
  });
}

// Count the home-page figures up from zero the first time they scroll into view.
const counters = document.querySelectorAll("[data-count]");
if (counters.length && "IntersectionObserver" in window && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      observer.unobserve(entry.target);
      const target = Number(entry.target.dataset.count);
      const start = performance.now();
      const tick = now => {
        const progress = Math.min(1, (now - start) / 1400);
        entry.target.textContent = Math.round(target * (1 - (1 - progress) ** 3));
        if (progress < 1) requestAnimationFrame(tick);
      };
      entry.target.textContent = "0";
      requestAnimationFrame(tick);
    }
  }, { threshold: .6 });
  counters.forEach(counter => observer.observe(counter));
}

// Type the home greeting out once; screen readers get the full text from the sr-only copy.
const typed = document.querySelector(".greeting .typed");
if (typed && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const characters = Array.from(typed.textContent);
  typed.textContent = "";
  typed.classList.add("typing");
  let shown = 0;
  const step = () => {
    typed.textContent = characters.slice(0, ++shown).join("");
    if (shown < characters.length) {
      // English greetings are about three times longer, so type them faster.
      const pause = /[，。！？～.!?]/.test(characters[shown - 1]) ? 240 : (UI.lang === "en" ? 14 : 42);
      setTimeout(step, pause);
    } else {
      setTimeout(() => typed.classList.remove("typing"), 2400);
    }
  };
  setTimeout(step, 450);
}

function resizeInput() {
  input.style.height = "39px";
  input.style.height = `${Math.max(39, Math.min(113, input.scrollHeight))}px`;
}
input.addEventListener("input", resizeInput);
input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
    event.preventDefault();
    form.requestSubmit();
  }
});

function message(text, question = false) {
  const article = document.createElement("article");
  article.className = question ? "message question" : "message";
  if (!question) {
    article.append(assistantAvatar.cloneNode(true));
  }
  const body = document.createElement("div");
  body.className = "message-body";
  const name = document.createElement("strong");
  name.className = "speaker";
  name.textContent = question ? UI.you : UI.assistant;
  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  body.append(name, paragraph);
  article.append(body);
  messages.append(article);
  return { article, body, paragraph };
}

// "Was this answer helpful?" with 👍 / 👎; one rating per answer.
function feedbackBar(question, result) {
  const bar = document.createElement("div");
  bar.className = "feedback";
  bar.setAttribute("role", "group");
  bar.setAttribute("aria-label", UI.feedback_ask);
  const label = document.createElement("span");
  label.textContent = UI.feedback_ask;
  bar.append(label);
  for (const [rating, icon, name] of [["up", "👍", UI.feedback_up], ["down", "👎", UI.feedback_down]]) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = icon;
    button.title = name;
    button.setAttribute("aria-label", name);
    button.addEventListener("click", async () => {
      for (const other of bar.querySelectorAll("button")) other.disabled = true;
      button.classList.add("chosen");
      try {
        const response = await fetch("/api/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question, rating, lang: UI.lang,
            answer: Array.from(result.answer).slice(0, 4000).join(""),
            sources: result.links.map(item => Array.from(item.title).slice(0, 200).join("")).slice(0, 4),
          }),
        });
        if (!response.ok) throw new Error();
        label.textContent = UI.feedback_thanks;
      } catch {
        label.textContent = UI.feedback_failed;
        button.classList.remove("chosen");
        for (const other of bar.querySelectorAll("button")) other.disabled = false;
      }
    });
    bar.append(button);
  }
  return bar;
}

function askSuggested(question) {
  if (send.disabled) return;
  input.value = question;
  form.requestSubmit();
}

for (const button of examples) {
  button.addEventListener("click", () => askSuggested(button.dataset.question || button.querySelector(".example-text").textContent));
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question || send.disabled) return;
  stopVoice();
  messages.querySelector(".follow-ups")?.remove();
  send.disabled = true;
  chat.classList.add("has-messages");
  for (const button of examples) button.disabled = true;
  message(question, true);
  input.value = "";
  resizeInput();
  const reply = message(UI.searching);
  reply.article.classList.add("pending");
  reply.paragraph.setAttribute("role", "status");
  const waiting = setTimeout(() => {
    reply.paragraph.textContent = UI.still_searching;
  }, 3500);
  messages.scrollTop = messages.scrollHeight;

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history: history.slice(-3), lang: UI.lang }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    history.push({ question, answer: Array.from(result.answer).slice(0, 1000).join("") });
    if (history.length > 3) history.shift();
    reply.paragraph.textContent = result.answer;
    if (result.links.length) {
      const label = document.createElement("span");
      label.className = "sources-label";
      label.textContent = UI.sources;
      reply.body.append(label);
    }
    for (const item of result.links) {
      const link = document.createElement("a");
      link.href = item.url;
      link.textContent = item.title;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      reply.body.append(link);
    }
    reply.body.append(feedbackBar(question, result));
    if (result.follow_ups?.length) {
      const suggestions = document.createElement("div");
      suggestions.className = "follow-ups";
      suggestions.setAttribute("role", "group");
      suggestions.setAttribute("aria-label", UI.follow_ups);
      for (const question of result.follow_ups) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = question;
        button.addEventListener("click", () => askSuggested(question));
        suggestions.append(button);
      }
      reply.body.append(suggestions);
    }
  } catch (error) {
    reply.article.classList.add("error");
    reply.paragraph.textContent = error.message || UI.offline;
    if (!input.value) {
      input.value = question;
      resizeInput();
    }
  } finally {
    clearTimeout(waiting);
    reply.paragraph.removeAttribute("role");
    send.disabled = false;
    reply.article.classList.remove("pending");
    for (const button of examples) button.disabled = false;
    messages.scrollTop = reply.article.offsetTop;
  }
});
