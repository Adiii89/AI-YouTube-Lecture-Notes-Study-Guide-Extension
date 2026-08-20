/**
 * AI YouTube Lecture Notes - Popup Controller (with Chat & Library)
 */

document.addEventListener("DOMContentLoaded", async () => {
  // State
  let currentVideoId = null;
  let currentVideoUrl = null;
  let currentNotesData = null;
  let chatHistory = [];
  let config = {
    apiUrl: "http://127.0.0.1:8000/api/v1",
    provider: "openai",
    modelName: ""
  };

  // DOM Elements - Header & Settings
  const statusIndicator = document.getElementById("status-indicator");
  const statusText = document.getElementById("status-text");
  const btnSettingsToggle = document.getElementById("btn-settings-toggle");
  const settingsPanel = document.getElementById("settings-panel");
  const apiUrlInput = document.getElementById("api-url-input");
  const providerSelect = document.getElementById("provider-select");
  const modelInput = document.getElementById("model-input");
  const btnSaveSettings = document.getElementById("btn-save-settings");
  const btnTestConnection = document.getElementById("btn-test-connection");

  // Top Nav
  const navTabs = document.querySelectorAll(".nav-tab");
  const pageContainers = document.querySelectorAll(".page-container");

  // Video Context
  const videoTitleEl = document.getElementById("video-title");
  const videoMetaEl = document.getElementById("video-meta");
  const customUrlContainer = document.getElementById("custom-url-container");
  const manualUrlInput = document.getElementById("manual-url-input");

  // Page 1: Notes Generator Elements
  const formView = document.getElementById("form-view");
  const loadingView = document.getElementById("loading-view");
  const resultView = document.getElementById("result-view");
  const formatCards = document.querySelectorAll(".format-card");
  const customPromptInput = document.getElementById("custom-prompt-input");
  const btnGenerate = document.getElementById("btn-generate");
  const loadingStepTitle = document.getElementById("loading-step-title");
  const loadingStepDesc = document.getElementById("loading-step-desc");

  const badgeFormat = document.getElementById("badge-format");
  const badgeWords = document.getElementById("badge-words");
  const badgeModel = document.getElementById("badge-model");
  const btnNewNote = document.getElementById("btn-new-note");

  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const markdownViewer = document.getElementById("markdown-viewer");
  const flashcardsContainer = document.getElementById("flashcards-container");
  const cornellContainer = document.getElementById("cornell-container");
  const fcCountEl = document.getElementById("fc-count");

  const btnCopyMd = document.getElementById("btn-copy-md");
  const btnDownloadMd = document.getElementById("btn-download-md");
  const btnPrint = document.getElementById("btn-print");

  // Page 2: Chat Elements
  const chatMessages = document.getElementById("chat-messages");
  const chatUserInput = document.getElementById("chat-user-input");
  const btnSendChat = document.getElementById("btn-send-chat");
  const quickChips = document.querySelectorAll(".quick-chip");

  // Page 3: Library Elements
  const librarySearchInput = document.getElementById("library-search-input");
  const libraryList = document.getElementById("library-list");

  // Error Banner
  const errorView = document.getElementById("error-view");
  const errorTitle = document.getElementById("error-title");
  const errorMessage = document.getElementById("error-message");
  const btnDismissError = document.getElementById("btn-dismiss-error");

  // -------------------------------------------------------------
  // Initialization
  // -------------------------------------------------------------
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    const saved = await chrome.storage.local.get(["apiUrl", "provider", "modelName"]);
    if (saved.apiUrl) config.apiUrl = saved.apiUrl;
    if (saved.provider) config.provider = saved.provider;
    if (saved.modelName) {
      if (config.provider === "openai" && saved.modelName.includes("gemini")) {
        config.modelName = "";
      } else if (config.provider === "gemini" && saved.modelName.includes("gpt")) {
        config.modelName = "";
      } else {
        config.modelName = saved.modelName;
      }
    }
  }
  apiUrlInput.value = config.apiUrl;
  providerSelect.value = config.provider || "openai";
  modelInput.value = config.modelName || "";

  checkBackendHealth();
  detectActiveTab();

  // -------------------------------------------------------------
  // Top Navigation Logic
  // -------------------------------------------------------------
  navTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      navTabs.forEach(t => t.classList.remove("active"));
      pageContainers.forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const targetPageId = `page-${tab.dataset.nav}`;
      const targetPage = document.getElementById(targetPageId);
      if (targetPage) {
        targetPage.classList.add("active");
        if (tab.dataset.nav === "library") {
          loadLibraryNotes();
        }
      }
    });
  });

  // Settings Panel
  btnSettingsToggle.addEventListener("click", () => {
    settingsPanel.classList.toggle("hidden");
  });

  providerSelect.addEventListener("change", () => {
    if (providerSelect.value === "openai") {
      modelInput.placeholder = "e.g. gpt-4o-mini (defaults to gpt-4o-mini)";
      if (modelInput.value.includes("gemini")) modelInput.value = "";
    } else if (providerSelect.value === "gemini") {
      modelInput.placeholder = "e.g. gemini-2.5-flash (defaults to gemini-2.5-flash)";
      if (modelInput.value.includes("gpt")) modelInput.value = "";
    }
  });

  btnSaveSettings.addEventListener("click", async () => {
    config.apiUrl = apiUrlInput.value.trim().replace(/\/$/, "");
    config.provider = providerSelect.value;
    config.modelName = modelInput.value.trim();
    if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
      await chrome.storage.local.set({
        apiUrl: config.apiUrl,
        provider: config.provider,
        modelName: config.modelName
      });
    }
    settingsPanel.classList.add("hidden");
    checkBackendHealth();
  });

  btnTestConnection.addEventListener("click", checkBackendHealth);
  btnDismissError.addEventListener("click", () => errorView.classList.add("hidden"));

  // Format selection
  formatCards.forEach(card => {
    card.addEventListener("click", () => {
      formatCards.forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      const radio = card.querySelector("input[type='radio']");
      if (radio) radio.checked = true;
    });
  });

  btnGenerate.addEventListener("click", handleGenerateNotes);

  btnNewNote.addEventListener("click", () => {
    resultView.classList.add("hidden");
    formView.classList.remove("hidden");
  });

  // Result Tabs
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const tabId = `tab-content-${btn.dataset.tab}`;
      const targetPane = document.getElementById(tabId);
      if (targetPane) targetPane.classList.add("active");
    });
  });

  btnCopyMd.addEventListener("click", () => {
    if (currentNotesData && currentNotesData.markdown_content) {
      navigator.clipboard.writeText(currentNotesData.markdown_content);
      const orig = btnCopyMd.innerHTML;
      btnCopyMd.innerText = "✓ Copied!";
      setTimeout(() => { btnCopyMd.innerHTML = orig; }, 2000);
    }
  });

  btnDownloadMd.addEventListener("click", () => {
    if (currentNotesData && currentNotesData.markdown_content) {
      const blob = new Blob([currentNotesData.markdown_content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const cleanTitle = (currentNotesData.title || "lecture_notes").replace(/[^a-zA-Z0-9_-]/g, "_");
      a.href = url;
      a.download = `${cleanTitle}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  });

  btnPrint.addEventListener("click", () => window.print());

  // -------------------------------------------------------------
  // Chat Feature Logic
  // -------------------------------------------------------------
  btnSendChat.addEventListener("click", sendChatMessage);
  chatUserInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  quickChips.forEach(chip => {
    chip.addEventListener("click", () => {
      chatUserInput.value = chip.dataset.query;
      sendChatMessage();
    });
  });

  async function sendChatMessage() {
    const question = chatUserInput.value.trim();
    if (!question) return;

    let urlOrId = currentVideoId || currentVideoUrl;
    if (!urlOrId && !customUrlContainer.classList.contains("hidden")) {
      urlOrId = manualUrlInput.value.trim();
    }

    if (!urlOrId) {
      showError("Missing Video", "Please open a YouTube video or paste a link to chat.");
      return;
    }

    // Append user message to UI
    appendChatMessage("user", question);
    chatUserInput.value = "";

    // Append typing bubble
    const typingId = appendTypingIndicator();

    const chosenProvider = config.provider === "auto" ? "openai" : config.provider;

    try {
      const response = await fetch(`${config.apiUrl}/notes/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url_or_id: urlOrId,
          question: question,
          chat_history: chatHistory,
          provider: chosenProvider,
          model_name: config.modelName || null
        })
      });

      removeTypingIndicator(typingId);

      if (!response.ok) {
        let err = `Chat error (${response.status})`;
        try {
          const errData = await response.json();
          err = errData.detail || err;
        } catch (e) {}
        throw new Error(err);
      }

      const data = await response.json();
      appendChatMessage("assistant", data.answer);

      // Save to chat history
      chatHistory.push({ role: "user", content: question });
      chatHistory.push({ role: "assistant", content: data.answer });

    } catch (err) {
      removeTypingIndicator(typingId);
      appendChatMessage("assistant", `⚠️ Failed to get answer: ${err.message}`);
    }
  }

  function appendChatMessage(role, text) {
    const msgEl = document.createElement("div");
    msgEl.className = `chat-msg chat-${role}`;

    const avatar = role === "user" ? "👤" : "🤖";
    const parsedText = role === "assistant" ? renderMarkdown(text) : escapeHtml(text);

    msgEl.innerHTML = `
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-bubble">${parsedText}</div>
    `;

    chatMessages.appendChild(msgEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendTypingIndicator() {
    const id = `typing-${Date.now()}`;
    const msgEl = document.createElement("div");
    msgEl.id = id;
    msgEl.className = "chat-msg chat-assistant";
    msgEl.innerHTML = `
      <div class="msg-avatar">🤖</div>
      <div class="msg-bubble" style="color: var(--text-muted);">
        <span style="animation: pulse 1s infinite;">Thinking & searching video...</span>
      </div>
    `;
    chatMessages.appendChild(msgEl);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return id;
  }

  function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // -------------------------------------------------------------
  // Library Logic
  // -------------------------------------------------------------
  librarySearchInput.addEventListener("input", () => {
    loadLibraryNotes(librarySearchInput.value.trim().toLowerCase());
  });

  async function loadLibraryNotes(searchTerm = "") {
    if (typeof chrome === "undefined" || !chrome.storage || !chrome.storage.local) {
      libraryList.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 20px;">Library available in Chrome extension mode.</p>`;
      return;
    }

    const allData = await chrome.storage.local.get(null);
    const notesKeys = Object.keys(allData).filter(k => k.startsWith("notes_"));

    if (notesKeys.length === 0) {
      libraryList.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 30px 10px;">No saved lecture notes yet. Generate notes on any YouTube video to save them here automatically!</p>`;
      return;
    }

    let notesList = notesKeys.map(k => ({ key: k, data: allData[k] }));

    if (searchTerm) {
      notesList = notesList.filter(item => {
        const title = (item.data.title || "").toLowerCase();
        const vid = (item.data.video_id || "").toLowerCase();
        return title.includes(searchTerm) || vid.includes(searchTerm);
      });
    }

    if (notesList.length === 0) {
      libraryList.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 20px;">No notes matching "${escapeHtml(searchTerm)}".</p>`;
      return;
    }

    libraryList.innerHTML = notesList.map(item => `
      <div class="library-card" data-key="${item.key}">
        <div class="lib-card-header">
          <span class="lib-card-title">${escapeHtml(item.data.title || "Lecture Notes")}</span>
          <span class="pill-badge pill-purple">${escapeHtml(formatLabel(item.data.note_format))}</span>
        </div>
        <div class="lib-card-meta">
          <span>🎬 ${escapeHtml(item.data.video_id || "Video")}</span>
          <span>•</span>
          <span>📝 ${item.data.word_count || 0} words</span>
        </div>
        <div class="lib-card-actions">
          <button class="btn btn-secondary btn-xs btn-open-lib" data-key="${item.key}">Open</button>
          <button class="btn btn-ghost btn-xs btn-del-lib" data-key="${item.key}" style="color: #f87171;">Delete</button>
        </div>
      </div>
    `).join("");

    // Open button listeners
    libraryList.querySelectorAll(".btn-open-lib").forEach(btn => {
      btn.addEventListener("click", () => {
        const key = btn.dataset.key;
        if (allData[key]) {
          currentNotesData = allData[key];
          // Switch to Notes Page
          navTabs[0].click();
          displayNotesResult(currentNotesData);
        }
      });
    });

    // Delete button listeners
    libraryList.querySelectorAll(".btn-del-lib").forEach(btn => {
      btn.addEventListener("click", async () => {
        const key = btn.dataset.key;
        await chrome.storage.local.remove([key]);
        loadLibraryNotes(librarySearchInput.value.trim().toLowerCase());
      });
    });
  }

  // -------------------------------------------------------------
  // Timestamp Click Handler (Event Delegation)
  // -------------------------------------------------------------
  document.addEventListener("click", (e) => {
    const badge = e.target.closest(".ts-badge");
    if (badge) {
      const seconds = parseFloat(badge.dataset.seconds);
      if (!isNaN(seconds)) {
        seekVideoInActiveTab(seconds);
      }
    }
  });

  // -------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------
  async function checkBackendHealth() {
    statusIndicator.className = "status-badge status-checking";
    statusText.innerText = "Connecting...";
    try {
      const resp = await fetch(`${config.apiUrl}/health`, { method: "GET" });
      if (resp.ok) {
        statusIndicator.className = "status-badge status-online";
        statusText.innerText = "API Online";
      } else {
        throw new Error(`HTTP ${resp.status}`);
      }
    } catch (err) {
      statusIndicator.className = "status-badge status-offline";
      statusText.innerText = "API Offline";
    }
  }

  async function detectActiveTab() {
    if (typeof chrome === "undefined" || !chrome.tabs) {
      showManualUrlPrompt();
      return;
    }

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.url) {
        showManualUrlPrompt();
        return;
      }

      currentVideoUrl = tab.url;
      const videoId = extractYouTubeId(tab.url);

      if (videoId) {
        currentVideoId = videoId;
        const pageTitle = tab.title ? tab.title.replace(/ - YouTube$/, "") : "YouTube Video";
        videoTitleEl.innerText = pageTitle;
        videoMetaEl.innerText = `Video ID: ${videoId}`;
        customUrlContainer.classList.add("hidden");

        checkCachedNotes(videoId);
      } else {
        showManualUrlPrompt();
      }
    } catch (e) {
      showManualUrlPrompt();
    }
  }

  function showManualUrlPrompt() {
    videoTitleEl.innerText = "Paste YouTube Video Link";
    videoMetaEl.innerText = "No active YouTube video detected";
    customUrlContainer.classList.remove("hidden");
  }

  function extractYouTubeId(url) {
    if (!url) return null;
    const match = url.match(/(?:watch\?v=|youtu\.be\/|shorts\/|embed\/)([a-zA-Z0-9_-]{11})/);
    return match ? match[1] : null;
  }

  async function checkCachedNotes(videoId) {
    if (typeof chrome === "undefined" || !chrome.storage || !chrome.storage.local) return;
    const selectedFormat = getSelectedFormat();
    const cacheKey = `notes_${videoId}_${selectedFormat}`;
    const result = await chrome.storage.local.get([cacheKey]);
    if (result[cacheKey]) {
      currentNotesData = result[cacheKey];
      displayNotesResult(currentNotesData);
    }
  }

  function getSelectedFormat() {
    const selectedRadio = document.querySelector("input[name='note-format']:checked");
    return selectedRadio ? selectedRadio.value : "comprehensive";
  }

  async function handleGenerateNotes() {
    errorView.classList.add("hidden");

    let urlOrId = currentVideoId || currentVideoUrl;
    if (!urlOrId && !customUrlContainer.classList.contains("hidden")) {
      urlOrId = manualUrlInput.value.trim();
    }

    if (!urlOrId) {
      showError("Missing Video", "Please open a YouTube video or enter a valid YouTube URL.");
      return;
    }

    const selectedFormat = getSelectedFormat();
    const customPrompt = customPromptInput.value.trim();
    const chosenProvider = config.provider === "auto" ? "openai" : config.provider;

    let modelToPass = config.modelName ? config.modelName.trim() : null;
    if (chosenProvider === "openai" && modelToPass && modelToPass.toLowerCase().includes("gemini")) {
      modelToPass = null;
    }
    if (chosenProvider === "gemini" && modelToPass && modelToPass.toLowerCase().includes("gpt")) {
      modelToPass = null;
    }

    formView.classList.add("hidden");
    loadingView.classList.remove("hidden");
    updateLoadingStep(1);

    try {
      const stepTimer = setTimeout(() => updateLoadingStep(2), 2500);

      const response = await fetch(`${config.apiUrl}/notes/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url_or_id: urlOrId,
          note_format: selectedFormat,
          provider: chosenProvider,
          custom_instructions: customPrompt || null,
          model_name: modelToPass
        })
      });

      clearTimeout(stepTimer);

      if (!response.ok) {
        let errDetail = `Server error (${response.status})`;
        try {
          const errData = await response.json();
          errDetail = errData.detail || errData.error || errDetail;
        } catch (e) {}
        throw new Error(errDetail);
      }

      const notesData = await response.json();
      currentNotesData = notesData;

      if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local && notesData.video_id) {
        const cacheKey = `notes_${notesData.video_id}_${selectedFormat}`;
        await chrome.storage.local.set({ [cacheKey]: notesData });
      }

      loadingView.classList.add("hidden");
      displayNotesResult(notesData);

    } catch (err) {
      loadingView.classList.add("hidden");
      formView.classList.remove("hidden");
      showError("Generation Failed", err.message);
    }
  }

  function updateLoadingStep(step) {
    if (step === 1) {
      loadingStepTitle.innerText = "Extracting Captions...";
      loadingStepDesc.innerText = "Retrieving YouTube transcripts & timestamp offsets";
    } else if (step === 2) {
      loadingStepTitle.innerText = "Synthesizing with AI...";
      loadingStepDesc.innerText = "Structuring educational lecture notes & study points";
    }
  }

  function displayNotesResult(notes) {
    formView.classList.add("hidden");
    resultView.classList.remove("hidden");

    badgeFormat.innerText = formatLabel(notes.note_format);
    badgeWords.innerText = `${notes.word_count || 0} words`;
    const modelDisplayName = (notes.model || "AI").replace("gemini-", "Gemini ").replace("gpt-", "GPT-");
    badgeModel.innerText = modelDisplayName;

    const renderedHtml = renderMarkdown(notes.markdown_content || "");
    markdownViewer.innerHTML = renderedHtml;

    const flashcards = notes.flashcards || [];
    fcCountEl.innerText = flashcards.length;
    if (flashcards.length > 0) {
      flashcardsContainer.innerHTML = flashcards.map((fc, idx) => `
        <div class="flashcard-item">
          <div class="fc-header">
            <span class="fc-question">Q${idx + 1}: ${escapeHtml(fc.question)}</span>
            ${fc.timestamp_cue ? renderTimestampBadge(fc.timestamp_cue) : ""}
          </div>
          <div class="fc-answer">
            <strong>Answer:</strong> ${escapeHtml(fc.answer)}
          </div>
        </div>
      `).join("");
    } else {
      flashcardsContainer.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 20px;">No flashcards in this format. Choose 'Flashcards' format to generate quiz items.</p>`;
    }

    const cornell = notes.cornell_notes || [];
    if (cornell.length > 0) {
      cornellContainer.innerHTML = `
        <table class="cornell-table">
          <thead>
            <tr>
              <th>Cue / Keyword</th>
              <th>Notes & Explanations</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            ${cornell.map(c => `
              <tr>
                <td class="cornell-cue">${escapeHtml(c.cue)}</td>
                <td>${escapeHtml(c.note)}</td>
                <td>${c.timestamp_str ? renderTimestampBadge(c.timestamp_str) : "-"}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    } else {
      cornellContainer.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 20px;">No Cornell cues in this format. Choose 'Cornell Notes' format for side-by-side tables.</p>`;
    }
  }

  function formatLabel(fmt) {
    switch (fmt) {
      case "comprehensive": return "Study Guide";
      case "cornell": return "Cornell Notes";
      case "summary": return "Summary";
      case "flashcards": return "Flashcards";
      case "action_items": return "Action Items";
      default: return "Lecture Notes";
    }
  }

  function renderTimestampBadge(tsStr) {
    const seconds = parseTimestampToSeconds(tsStr);
    return `<span class="ts-badge" data-seconds="${seconds}" title="Click to seek video to ${tsStr}">⏱️ ${tsStr}</span>`;
  }

  function parseTimestampToSeconds(ts) {
    if (!ts) return 0;
    const parts = ts.replace(/[\[\]]/g, "").trim().split(":").map(Number);
    if (parts.length === 2) {
      return parts[0] * 60 + parts[1];
    } else if (parts.length === 3) {
      return parts[0] * 3600 + parts[1] * 60 + parts[2];
    }
    return 0;
  }

  function seekVideoInActiveTab(seconds) {
    if (typeof chrome === "undefined" || !chrome.tabs) return;
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs && tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, {
          action: "SEEK_VIDEO",
          seconds: seconds
        });
      }
    });
  }

  function showError(title, msg) {
    errorTitle.innerText = title;
    errorMessage.innerText = msg;
    errorView.classList.remove("hidden");
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function renderMarkdown(md) {
    if (!md) return "";

    let html = escapeHtml(md);
    html = html.replace(/```(?:[a-zA-Z0-9]+)?\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/^\> (.*$)/gim, '<blockquote>$1</blockquote>');
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gim, '<ul>$1</ul>');
    html = html.replace(/\n\n/g, '<p></p>');

    html = html.replace(/\[(\d{1,2}:\d{2}(?::\d{2})?)\]/g, (match, p1) => {
      const sec = parseTimestampToSeconds(p1);
      return `<span class="ts-badge" data-seconds="${sec}" title="Seek video to ${p1}">⏱️ [${p1}]</span>`;
    });

    return html;
  }
});
