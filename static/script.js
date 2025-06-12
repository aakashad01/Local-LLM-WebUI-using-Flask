document.addEventListener("DOMContentLoaded", () => {
  const form       = document.getElementById("chat-form");
  const input      = document.getElementById("user_input");
  const chatWindow = document.getElementById("chat");
  const sessionId  = document.body.dataset.sessionId;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompt = input.value.trim();
    if (!prompt) return;

    // 1) Append user bubble
    const userBubble = document.createElement("div");
    userBubble.className = "message user";
    userBubble.textContent = prompt;
    chatWindow.appendChild(userBubble);
    scrollToBottom();

    input.value = "";
    input.focus();

    // 2) Append empty assistant bubble
    const aiBubble = document.createElement("div");
    aiBubble.className = "message assistant";
    chatWindow.appendChild(aiBubble);
    scrollToBottom();

    // 3) Send to /send
    const response = await fetch("/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, session_id: sessionId })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantText = "";

    // 4) Stream in chunks
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      assistantText += chunk;

      // Render markdown inline (still includes <think> tags)
      aiBubble.innerHTML = marked.parseInline(assistantText);
      scrollToBottom();
    }

    // 5) After complete message: setup toggle for <think> blocks
    setupThinkToggles();
    scrollToBottom();
  });

  function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function setupThinkToggles() {
    document.querySelectorAll("think").forEach(el => {
      // Avoid duplicate buttons
      if (el.dataset.toggleAdded) return;

      const btn = document.createElement("button");
      btn.textContent = "Show Thought";
      btn.className = "think-toggle";

      btn.addEventListener("click", () => {
        if (el.style.display === "none") {
          el.style.display = "block";
          btn.textContent = "Hide Thought";
        } else {
          el.style.display = "none";
          btn.textContent = "Show Thought";
        }
      });

      // Insert the button just before the <think> element
      el.parentNode.insertBefore(btn, el);
      el.style.display = "none";  // Start hidden
      el.dataset.toggleAdded = "true"; // Mark as processed
    });
  }
});
