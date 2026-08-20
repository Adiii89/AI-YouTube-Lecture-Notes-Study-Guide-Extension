/**
 * AI YouTube Lecture Notes - Content Script
 * Injects in-page buttons, manages the floating study sidebar, and handles video timestamp seeking.
 */

(function () {
  let sidebarEl = null;
  let currentVideoId = null;
  let currentFormat = "comprehensive";
  let cachedNotes = null;
  let inPageChatHistory = [];
  let apiUrl = "http://127.0.0.1:8000/api/v1";

  // Initialize
  init();

  function init() {
    loadSettings();
    injectNotesButton();

    // YouTube SPA navigation events
    window.addEventListener("yt-navigate-finish", onYouTubeNavigation);

    // MutationObserver as fallback for dynamic player rendering
    const observer = new MutationObserver(() => {
      injectNotesButton();
    });
    observer.observe(document.body, { childList: true, subtree: true });

    // Listen for messages from extension popup
    if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
      chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.action === "SEEK_VIDEO") {
          seekVideo(message.seconds);
          sendResponse({ success: true });
        }
      });
    }
  }

  async function loadSettings() {
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      const saved = await chrome.storage.local.get(["apiUrl"]);
      if (saved.apiUrl) apiUrl = saved.apiUrl;
    }
  }

  function onYouTubeNavigation() {
    currentVideoId = getYouTubeVideoId();
    cachedNotes = null;
    inPageChatHistory = [];
    injectNotesButton();
  }

  function getYouTubeVideoId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get("v") || null;
  }

  /**
   * Inject the "✨ AI Notes" action button into YouTube's watch page action toolbar
   */
  function injectNotesButton() {
    if (!window.location.pathname.startsWith("/watch")) return;
    if (document.getElementById("yt-ai-notes-injected-btn")) return;

    // Potential injection targets in YouTube DOM
    const targets = [
      "#top-row #actions #actions-inner",
      "#top-row #actions",
      "#actions-inner",
      "#owner",
      "#above-the-fold"
    ];

    let targetEl = null;
    for (const selector of targets) {
      targetEl = document.querySelector(selector);
      if (targetEl) break;
    }

    if (!targetEl) return;

    const btn = document.createElement("button");
    btn.id = "yt-ai-notes-injected-btn";
    btn.className = "yt-ai-notes-btn";
    btn.innerHTML = `
      <svg class="sparkle-icon" viewBox="0 0 24 24">
        <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z"/>
      </svg>
      <span>AI Notes</span>
    `;

    btn.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleSidebar();
    });

    targetEl.prepend(btn);
  }

  /**
   * Create or toggle the sliding in-page study drawer
   */
  function toggleSidebar() {
    if (!sidebarEl) {
      createSidebar();
    }
    sidebarEl.classList.toggle("open");
    if (sidebarEl.classList.contains("open")) {
      loadInPageNotes();
    }
  }

  function createSidebar() {
    sidebarEl = document.createElement("div");
    sidebarEl.id = "yt-ai-notes-sidebar";
    sidebarEl.innerHTML = `
      <div class="sidebar-header">
        <div class="sidebar-title-group">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="#8B5CF6">
            <path d="M12 2L2 7L12 12L22 7L12 2Z"/>
            <path d="M2 17L12 22L22 17" stroke="#8B5CF6" stroke-width="2"/>
            <path d="M2 12L12 17L22 12" stroke="#8B5CF6" stroke-width="2"/>
          </svg>
          <span class="sidebar-title">AI Lecture Notes</span>
        </div>
        <div class="sidebar-header-btns">
          <button id="sidebar-close-btn" class="sidebar-btn-close" title="Close Sidebar">✕</button>
        </div>
      </div>

      <div class="sidebar-body">
        <!-- Format Tabs -->
        <div class="sidebar-format-tabs">
          <button class="sidebar-tab-pill active" data-fmt="comprehensive">📚 Study Guide</button>
          <button class="sidebar-tab-pill" data-fmt="cornell">📝 Cornell</button>
          <button class="sidebar-tab-pill" data-fmt="summary">⚡ Summary</button>
          <button class="sidebar-tab-pill" data-fmt="flashcards">🗂️ Flashcards</button>
          <button class="sidebar-tab-pill" data-fmt="chat">💬 Chat</button>
        </div>

        <!-- Notes Output Container -->
        <div id="sidebar-notes-output" class="sidebar-notes-content">
          <p style="color: #94a3b8; text-align: center; padding: 20px;">Click generate to synthesize lecture notes for this video.</p>
        </div>

        <!-- Chat Container (Hidden by default) -->
        <div id="sidebar-chat-container" class="sidebar-chat-view" style="display: none; flex-direction: column; height: calc(100vh - 210px);">
          <div id="sidebar-chat-messages" style="flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; padding: 4px;">
            <div style="background: rgba(30,41,59,0.85); padding: 10px 12px; border-radius: 8px; font-size: 12px; border: 1px solid rgba(255,255,255,0.08); color: #cbd5e1;">
              🤖 Hi! I'm your video study partner. Ask me any question about this lecture, formulas, or timestamps!
            </div>
          </div>
          <div style="display: flex; gap: 6px; padding-top: 4px; border-top: 1px solid rgba(255,255,255,0.08);">
            <input type="text" id="sidebar-chat-input" placeholder="Ask anything about this video..." style="flex: 1; padding: 9px 14px; background: rgba(0,0,0,0.5); border: 1px solid rgba(139,92,246,0.3); border-radius: 20px; color: #fff; font-size: 12px; outline: none;">
            <button id="sidebar-chat-send-btn" style="background: #8b5cf6; border: none; color: #fff; width: 34px; height: 34px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: bold;">➤</button>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <button id="sidebar-generate-btn" class="sidebar-action-btn" style="background: #8b5cf6; border-color: #8b5cf6;">✨ Generate Notes</button>
        <button id="sidebar-copy-btn" class="sidebar-action-btn">📋 Copy</button>
      </div>
    `;

    document.body.appendChild(sidebarEl);

    // Event listeners
    document.getElementById("sidebar-close-btn").addEventListener("click", () => {
      sidebarEl.classList.remove("open");
    });

    // Format Tab clicks
    const tabs = sidebarEl.querySelectorAll(".sidebar-tab-pill");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        currentFormat = tab.dataset.fmt;

        const notesOut = document.getElementById("sidebar-notes-output");
        const chatCont = document.getElementById("sidebar-chat-container");
        const genBtn = document.getElementById("sidebar-generate-btn");
        const copyBtn = document.getElementById("sidebar-copy-btn");

        if (currentFormat === "chat") {
          notesOut.style.display = "none";
          chatCont.style.display = "flex";
          genBtn.style.display = "none";
          copyBtn.style.display = "none";
        } else {
          notesOut.style.display = "block";
          chatCont.style.display = "none";
          genBtn.style.display = "inline-block";
          copyBtn.style.display = "inline-block";
          loadInPageNotes();
        }
      });
    });

    // Generate button
    document.getElementById("sidebar-generate-btn").addEventListener("click", generateInPageNotes);

    // Copy button
    document.getElementById("sidebar-copy-btn").addEventListener("click", () => {
      if (cachedNotes && cachedNotes.markdown_content) {
        navigator.clipboard.writeText(cachedNotes.markdown_content);
        const copyBtn = document.getElementById("sidebar-copy-btn");
        copyBtn.innerText = "✓ Copied!";
        setTimeout(() => { copyBtn.innerText = "📋 Copy"; }, 2000);
      }
    });

    // In-page Chat send
    const chatInput = document.getElementById("sidebar-chat-input");
    const chatSendBtn = document.getElementById("sidebar-chat-send-btn");

    chatSendBtn.addEventListener("click", sendInPageChat);
    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        sendInPageChat();
      }
    });

    // Timestamp clicks in sidebar
    sidebarEl.addEventListener("click", (e) => {
      const badge = e.target.closest(".inpage-ts-badge");
      if (badge) {
        const seconds = parseFloat(badge.dataset.seconds);
        if (!isNaN(seconds)) {
          seekVideo(seconds);
        }
      }
    });
  }

  async function sendInPageChat() {
    const chatInput = document.getElementById("sidebar-chat-input");
    const q = chatInput.value.trim();
    if (!q) return;

    const videoId = getYouTubeVideoId();
    if (!videoId) return;

    const chatMsgs = document.getElementById("sidebar-chat-messages");

    // Add user bubble
    chatMsgs.innerHTML += `
      <div style="align-self: flex-end; background: #7c3aed; padding: 6px 10px; border-radius: 8px; font-size: 12px; color: #fff; max-width: 85%;">
        ${escapeHtml(q)}
      </div>
    `;
    chatInput.value = "";
    chatMsgs.scrollTop = chatMsgs.scrollHeight;

    // Loading indicator
    const loadId = `load-${Date.now()}`;
    chatMsgs.innerHTML += `<div id="${loadId}" style="color: #94a3b8; font-size: 11px;">Thinking...</div>`;
    chatMsgs.scrollTop = chatMsgs.scrollHeight;

    try {
      let provider = "openai";
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        const saved = await chrome.storage.local.get(["provider"]);
        if (saved.provider && saved.provider !== "auto") provider = saved.provider;
      }

      const response = await fetch(`${apiUrl}/notes/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url_or_id: videoId,
          question: q,
          chat_history: inPageChatHistory,
          provider: provider
        })
      });

      const loadEl = document.getElementById(loadId);
      if (loadEl) loadEl.remove();

      if (!response.ok) {
        throw new Error(`Chat error (${response.status})`);
      }

      const data = await response.json();
      let formattedAnswer = escapeHtml(data.answer);
      formattedAnswer = formattedAnswer.replace(/\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g, (match, p1) => {
        const sec = parseTimestamp(p1);
        return `<span class="inpage-ts-badge" data-seconds="${sec}">⏱️ [${p1}]</span>`;
      });

      chatMsgs.innerHTML += `
        <div style="align-self: flex-start; background: rgba(30,41,59,0.85); padding: 8px 10px; border-radius: 8px; font-size: 12px; color: #cbd5e1; border: 1px solid rgba(255,255,255,0.08); max-width: 90%;">
          ${formattedAnswer}
        </div>
      `;
      chatMsgs.scrollTop = chatMsgs.scrollHeight;

      inPageChatHistory.push({ role: "user", content: q });
      inPageChatHistory.push({ role: "assistant", content: data.answer });

    } catch (err) {
      const loadEl = document.getElementById(loadId);
      if (loadEl) loadEl.remove();
      chatMsgs.innerHTML += `<div style="color: #f87171; font-size: 11px;">⚠️ ${escapeHtml(err.message)}</div>`;
    }
  }

  async function loadInPageNotes() {
    const videoId = getYouTubeVideoId();
    if (!videoId) return;

    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      const cacheKey = `notes_${videoId}_${currentFormat}`;
      const saved = await chrome.storage.local.get([cacheKey]);
      if (saved[cacheKey]) {
        cachedNotes = saved[cacheKey];
        renderSidebarContent(cachedNotes);
        return;
      }
    }
  }

  async function generateInPageNotes() {
    const videoId = getYouTubeVideoId();
    if (!videoId) {
      alert("No active YouTube video detected.");
      return;
    }

    const outputEl = document.getElementById("sidebar-notes-output");
    outputEl.innerHTML = `
      <div style="text-align: center; padding: 40px 10px; color: #c4b5fd;">
        <div style="font-size: 24px; margin-bottom: 8px; animation: spin 1s linear infinite;">⏳</div>
        <strong>Synthesizing AI Lecture Notes...</strong>
        <p style="font-size: 11px; color: #94a3b8; margin-top: 6px;">Extracting transcripts and generating structured notes</p>
      </div>
    `;

    try {
      let provider = "openai";
      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        const saved = await chrome.storage.local.get(["provider"]);
        if (saved.provider && saved.provider !== "auto") provider = saved.provider;
      }

      const response = await fetch(`${apiUrl}/notes/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url_or_id: videoId,
          note_format: currentFormat,
          provider: provider
        })
      });

      if (!response.ok) {
        let err = `Error (${response.status})`;
        try {
          const data = await response.json();
          err = data.detail || err;
        } catch (e) {}
        throw new Error(err);
      }

      const notes = await response.json();
      cachedNotes = notes;

      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
        const cacheKey = `notes_${videoId}_${currentFormat}`;
        await chrome.storage.local.set({ [cacheKey]: notes });
      }

      renderSidebarContent(notes);
    } catch (err) {
      outputEl.innerHTML = `
        <div style="padding: 16px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #fca5a5;">
          <strong>Generation Failed</strong>
          <p style="font-size: 11px; margin-top: 4px;">${escapeHtml(err.message)}</p>
        </div>
      `;
    }
  }

  function renderSidebarContent(notes) {
    const outputEl = document.getElementById("sidebar-notes-output");
    if (!outputEl) return;

    let html = escapeHtml(notes.markdown_content || "");

    // Code blocks
    html = html.replace(/```(?:[a-zA-Z0-9]+)?\n([\s\S]*?)```/g, '<pre style="background: rgba(0,0,0,0.5); padding: 8px; border-radius: 6px; overflow-x: auto;"><code>$1</code></pre>');

    // Headers
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold & Italic
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Lists
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');

    // Timestamps
    html = html.replace(/\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g, (match, p1) => {
      const sec = parseTimestamp(p1);
      return `<span class="inpage-ts-badge" data-seconds="${sec}" title="Seek video to ${p1}">⏱️ [${p1}]</span>`;
    });

    outputEl.innerHTML = html;
  }

  function seekVideo(seconds) {
    const video = document.querySelector("video");
    if (video) {
      video.currentTime = seconds;
      video.play();
    }
  }

  function parseTimestamp(ts) {
    if (!ts) return 0;
    const parts = ts.trim().split(":").map(Number);
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return 0;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
})();
