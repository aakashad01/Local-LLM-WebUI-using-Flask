document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("chat-form");
  const input = document.getElementById("user_input");
  const chatWindow = document.getElementById("chat");
  const sessionId = document.body.dataset.sessionId;

  // Theme Toggle
  window.toggleTheme = () => {
    document.body.classList.toggle("dark");
    localStorage.setItem("theme", document.body.classList.contains("dark") ? "dark" : "light");
  };

  // Apply saved theme on load
  if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark");
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const prompt = input.value.trim();
    if (!prompt) return;

    const userBubble = document.createElement("div");
    userBubble.className = "message user";
    userBubble.textContent = prompt;
    chatWindow.appendChild(userBubble);
    scrollToBottom();

    input.value = "";
    input.focus();

    const aiBubble = document.createElement("div");
    aiBubble.className = "message assistant";
    chatWindow.appendChild(aiBubble);
    scrollToBottom();

    const response = await fetch("/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, session_id: sessionId })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantText = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      assistantText += chunk;

      const displayText = assistantText.replace(/<think>([\s\S]*?)<\/think>/g, '');
      aiBubble.innerHTML = marked.parseInline(displayText);
      scrollToBottom();
    }

    const thinkMatch = assistantText.match(/<think>([\s\S]*?)<\/think>/);
    if (thinkMatch) {
      const btn = document.createElement("button");
      btn.className = "think-toggle";
      btn.innerText = "💭 Show Thought";
      const block = document.createElement("div");
      block.className = "think-block";
      block.innerText = thinkMatch[1];
      block.style.display = "none";
      btn.onclick = () => {
        block.style.display = block.style.display === "none" ? "block" : "none";
        btn.innerText = block.style.display === "none" ? "💭 Show Thought" : "🙈 Hide Thought";
      };
      aiBubble.appendChild(btn);
      aiBubble.appendChild(block);
    }

    scrollToBottom();
  });

  function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  window.renameSession = (sid) => {
    const name = prompt("Rename this session:");
    if (name) {
      fetch(`/rename_session?sid=${encodeURIComponent(sid)}&name=${encodeURIComponent(name)}`)
        .then(() => location.reload());
    }
  };

  window.deleteSession = (sid) => {
    if (confirm("Are you sure you want to delete this session?")) {
      fetch(`/delete_session?sid=${encodeURIComponent(sid)}`)
        .then(() => location.href = "/?session_id=new");
    }
  };
});
