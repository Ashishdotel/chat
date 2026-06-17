/**
 * app.js — Nepali Chatbot + Language Translator Frontend Logic
 */

"use strict";

// ===================== STATE =====================
const STATE = {
  sessionId: null,
  messageCount: 0,
  isLoading: false,
  apiBase: "",
  lastResponseWasRAG: false,
  chatLanguage: "ne",
  activeTab: "chat",
  activeSubtab: "text",
  translating: false,
};

const SESSION_KEY     = "nepali_chatbot_session_id";
const CHAT_LANG_KEY   = "nepali_chatbot_language";

// ===================== DOM REFERENCES =====================
const DOM = {
  chatMessages:        document.getElementById("chatMessages"),
  messageInput:        document.getElementById("messageInput"),
  btnSend:             document.getElementById("btnSend"),
  btnNewChat:          document.getElementById("btnNewChat"),
  typingIndicator:     document.getElementById("typingIndicator"),
  errorBanner:         document.getElementById("errorBanner"),
  errorMessage:        document.getElementById("errorMessage"),
  sessionIdDisplay:    document.getElementById("sessionIdDisplay"),
  messageCountDisplay: document.getElementById("messageCountDisplay"),
  statusDisplay:       document.getElementById("statusDisplay"),
  welcomeScreen:       document.getElementById("welcomeScreen"),
  charCount:           document.getElementById("charCount"),
  modelBadge:          document.getElementById("modelBadge"),
  chatLanguageSelect:  document.getElementById("chatLanguageSelect"),
};

// ===================== TAB SWITCHING =====================

window.switchMainTab = function(tab) {
  STATE.activeTab = tab;
  document.getElementById("panelChat").classList.toggle("hidden", tab !== "chat");
  document.getElementById("panelTranslate").classList.toggle("hidden", tab !== "translate");
  document.getElementById("tabChat").classList.toggle("active", tab === "chat");
  document.getElementById("tabTranslate").classList.toggle("active", tab === "translate");
};

window.switchSubtab = function(sub) {
  STATE.activeSubtab = sub;
  document.getElementById("translateTextPanel").classList.toggle("hidden", sub !== "text");
  document.getElementById("translateDocPanel").classList.toggle("hidden", sub !== "document");
  document.getElementById("subtabText").classList.toggle("active", sub === "text");
  document.getElementById("subtabDoc").classList.toggle("active", sub === "document");
};

// ===================== SESSION MANAGEMENT =====================

function loadSession() {
  const savedSession = localStorage.getItem(SESSION_KEY);
  if (savedSession) {
    STATE.sessionId = savedSession;
  }
  const savedLang = localStorage.getItem(CHAT_LANG_KEY);
  if (savedLang && DOM.chatLanguageSelect) {
    STATE.chatLanguage = savedLang;
    DOM.chatLanguageSelect.value = savedLang;
  }
  updateSessionUI();
}

function saveSession(sessionId) {
  STATE.sessionId = sessionId;
  localStorage.setItem(SESSION_KEY, sessionId);
  updateSessionUI();
}

async function clearSession() {
  if (!STATE.sessionId) { resetUI(); return; }
  try {
    await fetch(`${STATE.apiBase}/api/chat/${STATE.sessionId}`, { method: "DELETE" });
  } catch (err) {
    console.warn("[Session] Failed to clear backend session:", err);
  }
  localStorage.removeItem(SESSION_KEY);
  STATE.sessionId = null;
  STATE.messageCount = 0;
  resetUI();
}

function updateSessionUI() {
  if (STATE.sessionId) {
    DOM.sessionIdDisplay.textContent = STATE.sessionId.substring(0, 8) + "...";
    DOM.sessionIdDisplay.title = STATE.sessionId;
  } else {
    DOM.sessionIdDisplay.textContent = "—";
  }
  DOM.messageCountDisplay.textContent = STATE.messageCount;
}

// ===================== LANGUAGE SELECTION (CHAT) =====================

if (DOM.chatLanguageSelect) {
  DOM.chatLanguageSelect.addEventListener("change", () => {
    STATE.chatLanguage = DOM.chatLanguageSelect.value;
    localStorage.setItem(CHAT_LANG_KEY, STATE.chatLanguage);
  });
}

// ===================== API COMMUNICATION (CHAT) =====================

async function sendMessageToAPI(message) {
  const payload = {
    message:    message,
    session_id: STATE.sessionId,
    language:   STATE.chatLanguage,
  };
  const response = await fetch(`${STATE.apiBase}/api/chat`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(payload),
  });
  if (!response.ok) {
    let errorDetail = "अज्ञात त्रुटि भयो।";
    try {
      const errData = await response.json();
      if (errData.detail?.detail) errorDetail = errData.detail.detail;
      else if (errData.detail)    errorDetail = String(errData.detail);
    } catch (_) {}
    throw new Error(errorDetail);
  }
  return await response.json();
}

// ===================== MAIN SEND FLOW =====================

async function handleSend() {
  const message = DOM.messageInput.value.trim();
  if (!message || STATE.isLoading) return;

  setLoading(true);
  hideError();

  if (DOM.welcomeScreen) DOM.welcomeScreen.style.display = "none";

  const sentMessage = message;
  DOM.messageInput.value = "";
  updateCharCount();
  autoResizeInput();

  appendMessage("user", sentMessage);
  showTypingIndicator();

  try {
    const data = await sendMessageToAPI(sentMessage);

    if (data.session_id) saveSession(data.session_id);

    if (data.model_used) {
      DOM.modelBadge.textContent = data.model_used.toUpperCase().replace("GPT-", "GPT ");
    }

    STATE.messageCount++;
    DOM.messageCountDisplay.textContent = STATE.messageCount;

    hideTypingIndicator();
    STATE.lastResponseWasRAG = data.rag_used || false;
    appendMessage("bot", data.reply);

  } catch (err) {
    hideTypingIndicator();
    showError(err.message || "माफ गर्नुहोस्, जवाफ दिन सकिएन।");
    console.error("[API] Error:", err);
  } finally {
    setLoading(false);
  }
}

// ===================== UI RENDERING (CHAT) =====================

function appendMessage(sender, text) {
  const isUser = sender === "user";
  const messageEl = document.createElement("div");
  messageEl.classList.add("message", isUser ? "user" : "bot");

  const avatar = document.createElement("div");
  avatar.classList.add("message-avatar");
  avatar.textContent = isUser ? "👤" : "🤖";

  const content = document.createElement("div");
  content.classList.add("message-content");

  const bubble = document.createElement("div");
  bubble.classList.add("message-bubble");
  bubble.textContent = text;

  const timeEl = document.createElement("div");
  timeEl.classList.add("message-time");
  timeEl.textContent = getCurrentTime();

  content.appendChild(bubble);
  content.appendChild(timeEl);
  messageEl.appendChild(avatar);
  messageEl.appendChild(content);
  DOM.chatMessages.appendChild(messageEl);

  if (!isUser && STATE.lastResponseWasRAG) {
    const bubbleEl = messageEl.querySelector(".message-bubble");
    if (bubbleEl && !bubbleEl.querySelector(".rag-indicator")) {
      const badge = document.createElement("span");
      badge.className = "rag-indicator";
      badge.textContent = "📄 RAG";
      bubbleEl.appendChild(badge);
    }
    STATE.lastResponseWasRAG = false;
  }
  scrollToBottom();
}

function getCurrentTime() {
  const now = new Date();
  return now.toLocaleTimeString("ne-NP", { hour: "2-digit", minute: "2-digit", hour12: true });
}

function scrollToBottom() {
  requestAnimationFrame(() => { DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight; });
}

function showTypingIndicator() { DOM.typingIndicator.style.display = "flex"; scrollToBottom(); }
function hideTypingIndicator() { DOM.typingIndicator.style.display = "none"; }

function showError(msg) {
  DOM.errorMessage.textContent = msg;
  DOM.errorBanner.style.display = "flex";
}
function hideError() { DOM.errorBanner.style.display = "none"; }
window.hideError = hideError;

function setLoading(loading) {
  STATE.isLoading = loading;
  DOM.messageInput.disabled = loading;
  DOM.btnSend.disabled = loading || DOM.messageInput.value.trim().length === 0;
  const badge = DOM.statusDisplay;
  if (loading) {
    badge.textContent = "लोड हुँदैछ...";
    badge.className   = "status-badge status-loading";
  } else {
    badge.textContent = "तयार";
    badge.className   = "status-badge status-idle";
  }
}

function resetUI() {
  DOM.chatMessages.innerHTML = `
    <div class="welcome-screen" id="welcomeScreen">
      <div class="welcome-icon">🙏</div>
      <h2>नमस्ते!</h2>
      <p>म तपाईंको नेपाली भाषा सहायक हुँ।</p>
      <p class="welcome-sub">I am your multilingual assistant.<br/>Select your language above and ask me anything!</p>
      <div class="suggestion-chips">
        <button class="chip" data-msg="नेपालको राजधानी कुन हो?">🏔️ नेपालको राजधानी कुन हो?</button>
        <button class="chip" data-msg="What does 'स्वतन्त्रता' mean in English?">🔤 What does 'स्वतन्त्रता' mean?</button>
        <button class="chip" data-msg="मलाई नेपाली व्याकरण सिकाउनुहोस्।">📚 नेपाली व्याकरण सिकाउनुहोस्</button>
        <button class="chip" data-msg="Translate 'Hello, how are you?' to Nepali">🌐 Translate to Nepali</button>
      </div>
    </div>`;
  DOM.welcomeScreen = document.getElementById("welcomeScreen");
  bindChipEvents();
  STATE.messageCount = 0;
  STATE.isLoading    = false;
  updateSessionUI();
  hideError();
  DOM.messageInput.value = "";
  updateCharCount();
  DOM.messageInput.focus();
}

// ===================== INPUT HANDLING =====================

function autoResizeInput() {
  const input = DOM.messageInput;
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 120) + "px";
}

function updateCharCount() {
  const len = DOM.messageInput.value.length;
  DOM.charCount.textContent = `${len}/2000`;
  DOM.charCount.style.color = len > 1800 ? "var(--error)" : "var(--text-muted)";
}

function updateSendButton() {
  DOM.btnSend.disabled = DOM.messageInput.value.trim().length === 0 || STATE.isLoading;
}

// ===================== SUGGESTION CHIPS =====================

function bindChipEvents() {
  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const msg = chip.getAttribute("data-msg");
      if (msg) {
        DOM.messageInput.value = msg;
        updateCharCount();
        updateSendButton();
        autoResizeInput();
        handleSend();
      }
    });
  });
}

// ===================== EVENT LISTENERS (CHAT) =====================

DOM.btnSend.addEventListener("click", handleSend);

DOM.messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

DOM.messageInput.addEventListener("input", () => {
  updateCharCount();
  autoResizeInput();
  updateSendButton();
});

DOM.btnNewChat.addEventListener("click", () => {
  if (STATE.isLoading) return;
  if (STATE.messageCount > 0) {
    if (!confirm("नयाँ कुराकानी सुरु गर्नुहोस्?\n(Start a new conversation?)")) return;
  }
  clearSession();
});

DOM.messageInput.addEventListener("paste", () => {
  setTimeout(() => { updateCharCount(); updateSendButton(); autoResizeInput(); }, 0);
});

// ===================== HISTORY PANEL =====================

async function loadSessionHistory() {
  const historyList = document.getElementById("historyList");
  if (!historyList) return;
  try {
    const response = await fetch(`${STATE.apiBase}/api/sessions/`);
    if (!response.ok) throw new Error("Failed to fetch sessions");
    const sessions = await response.json();
    if (sessions.length === 0) {
      historyList.innerHTML = `<p class="history-empty">कुनै पुरानो कुराकानी छैन।<br/><small>No past conversations.</small></p>`;
      return;
    }
    historyList.innerHTML = sessions.map(session => `
      <button class="history-item ${session.id === STATE.sessionId ? 'active' : ''}"
        data-session-id="${session.id}" onclick="loadPastSession('${session.id}')">
        <span class="history-item-icon">💬</span>
        <span class="history-item-text">
          <span class="history-item-title">${escapeHtml(session.title)}</span>
          <span class="history-item-meta">${session.message_count} messages · ${formatRelativeTime(session.updated_at)}</span>
        </span>
        <button class="history-item-delete" title="Delete" onclick="deleteHistoryItem(event, '${session.id}')">✕</button>
      </button>`).join("");
  } catch (err) {
    console.error("[History] Failed to load sessions:", err);
    historyList.innerHTML = `<p class="history-empty" style="color:var(--error)">इतिहास लोड गर्न सकिएन。<br/><small>Could not load history.</small></p>`;
  }
}

async function loadPastSession(sessionId) {
  if (STATE.isLoading || sessionId === STATE.sessionId) return;
  try {
    const response = await fetch(`${STATE.apiBase}/api/sessions/${sessionId}`);
    if (!response.ok) throw new Error("Session not found");
    const data = await response.json();
    saveSession(sessionId);
    STATE.messageCount = data.message_count;
    DOM.messageCountDisplay.textContent = STATE.messageCount;
    DOM.chatMessages.innerHTML = "";
    data.messages.forEach(msg => appendMessage(msg.role === "user" ? "user" : "bot", msg.content));
    document.querySelectorAll(".history-item").forEach(el => {
      el.classList.toggle("active", el.dataset.sessionId === sessionId);
    });
    DOM.messageInput.focus();
  } catch (err) {
    console.error("[History] Failed to load session:", err);
    showError("पुरानो कुराकानी लोड गर्न सकिएन।");
  }
}

async function deleteHistoryItem(event, sessionId) {
  event.stopPropagation();
  if (!confirm("यो कुराकानी मेट्नुहोस्?\n(Delete this conversation?)")) return;
  try {
    await fetch(`${STATE.apiBase}/api/sessions/${sessionId}`, { method: "DELETE" });
    if (sessionId === STATE.sessionId) {
      localStorage.removeItem(SESSION_KEY);
      STATE.sessionId = null;
      STATE.messageCount = 0;
      resetUI();
    }
    await loadSessionHistory();
  } catch (err) {
    console.error("[History] Delete failed:", err);
    showError("मेट्न सकिएन।");
  }
}

function formatRelativeTime(isoString) {
  const date     = new Date(isoString);
  const now      = new Date();
  const diffMins = Math.floor((now - date) / 60000);
  const diffHours = Math.floor((now - date) / 3600000);
  const diffDays  = Math.floor((now - date) / 86400000);
  if (diffMins < 1)  return "भर्खरै";
  if (diffMins < 60) return `${diffMins} मिनेट अघि`;
  if (diffHours < 24) return `${diffHours} घण्टा अघि`;
  if (diffDays < 7)   return `${diffDays} दिन अघि`;
  return date.toLocaleDateString("ne-NP");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// ===================== RAG / DOCUMENT UPLOAD =====================

async function loadRAGStatus() {
  try {
    const response = await fetch(`${STATE.apiBase}/api/documents/status`);
    if (!response.ok) return;
    const data = await response.json();
    const badge = document.getElementById("ragBadge");
    if (badge) {
      badge.textContent = data.rag_enabled ? "ON" : "OFF";
      badge.className   = `rag-badge${data.rag_enabled ? " active" : ""}`;
    }
    renderDocumentList(data.documents);
  } catch (err) {
    console.error("[RAG] Failed to load status:", err);
  }
}

function renderDocumentList(documents) {
  const docList = document.getElementById("docList");
  if (!docList) return;
  if (!documents || documents.length === 0) {
    docList.innerHTML = `<p class="doc-empty">कुनै दस्तावेज छैन।<br/><small>No documents indexed.</small></p>`;
    return;
  }
  docList.innerHTML = documents.map(doc => `
    <div class="doc-item">
      <span class="doc-item-icon">📄</span>
      <div class="doc-item-info">
        <span class="doc-item-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
        <span class="doc-item-meta">${doc.page_count} pages · ${doc.chunk_count} chunks</span>
      </div>
      <button class="doc-item-delete" title="Remove" onclick="removeDocument('${escapeHtml(doc.filename)}')">✕</button>
    </div>`).join("");
}

async function uploadDocument(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) { showError("केवल PDF फाइल अपलोड गर्न सकिन्छ।"); return; }
  if (file.size > 50 * 1024 * 1024) { showError("फाइल 50MB भन्दा सानो हुनुपर्छ।"); return; }

  const dropZone       = document.getElementById("dropZone");
  const uploadProgress = document.getElementById("uploadProgress");
  const progressFill   = document.getElementById("progressFill");
  const progressLabel  = document.getElementById("progressLabel");

  if (dropZone)      dropZone.style.display      = "none";
  if (uploadProgress) uploadProgress.style.display = "flex";

  let progress = 0;
  const progressInterval = setInterval(() => {
    progress = Math.min(progress + Math.random() * 8, 80);
    if (progressFill) progressFill.style.width = `${progress}%`;
  }, 200);

  if (progressLabel) progressLabel.textContent = `'${file.name}' प्रक्रिया हुँदैछ...`;

  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${STATE.apiBase}/api/documents/upload`, { method: "POST", body: formData });
    clearInterval(progressInterval);
    if (!response.ok) { const err = await response.json(); throw new Error(err.detail || "Upload failed"); }
    const data = await response.json();
    if (progressFill) progressFill.style.width = "100%";
    if (progressLabel) progressLabel.textContent = `✓ ${data.chunk_count} chunks indexed from ${data.page_count} pages`;
    setTimeout(() => {
      if (dropZone)      dropZone.style.display      = "block";
      if (uploadProgress) uploadProgress.style.display = "none";
      if (progressFill)  progressFill.style.width = "0%";
    }, 2000);
    await loadRAGStatus();
  } catch (err) {
    clearInterval(progressInterval);
    if (dropZone)      dropZone.style.display      = "block";
    if (uploadProgress) uploadProgress.style.display = "none";
    if (progressFill)  progressFill.style.width = "0%";
    showError(`अपलोड असफल: ${err.message}`);
    console.error("[RAG] Upload error:", err);
  }
}

async function removeDocument(filename) {
  if (!confirm(`'${filename}' हटाउने?`)) return;
  try {
    const response = await fetch(`${STATE.apiBase}/api/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
    if (!response.ok) throw new Error("Delete failed");
    await loadRAGStatus();
  } catch (err) {
    showError("दस्तावेज हटाउन सकिएन।");
    console.error("[RAG] Remove error:", err);
  }
}

const fileInput  = document.getElementById("fileInput");
const dropZone   = document.getElementById("dropZone");
const btnBrowse  = document.getElementById("btnBrowse");

if (btnBrowse && fileInput) btnBrowse.addEventListener("click", () => fileInput.click());
if (fileInput) {
  fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) uploadDocument(file);
    fileInput.value = "";
  });
}
if (dropZone) {
  dropZone.addEventListener("click", () => fileInput && fileInput.click());
  dropZone.addEventListener("dragover",  (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
  dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) uploadDocument(file);
  });
}

const btnRefreshHistory = document.getElementById("btnRefreshHistory");
if (btnRefreshHistory) btnRefreshHistory.addEventListener("click", loadSessionHistory);

// ===================== TEXT TRANSLATOR =====================

const sourceTextEl = document.getElementById("sourceText");
const sourceLangEl = document.getElementById("sourceLang");
const targetLangEl = document.getElementById("targetLang");

if (sourceTextEl) {
  sourceTextEl.addEventListener("input", () => {
    const len = sourceTextEl.value.length;
    const counter = document.getElementById("sourceCharCount");
    if (counter) {
      counter.textContent   = `${len} / 5000`;
      counter.style.color   = len > 4500 ? "var(--error)" : "var(--text-muted)";
    }
  });
}

document.getElementById("btnSwapLangs")?.addEventListener("click", () => {
  if (!sourceLangEl || !targetLangEl) return;
  const src = sourceLangEl.value;
  const tgt = targetLangEl.value;
  if (src === "auto") return;
  sourceLangEl.value = tgt;
  targetLangEl.value = src;
  // Also swap text content
  const outputEl = document.getElementById("translationOutput");
  const srcText  = sourceTextEl?.value || "";
  const outText  = outputEl?.dataset.translatedText || "";
  if (sourceTextEl && outText) {
    sourceTextEl.value = outText;
    sourceTextEl.dispatchEvent(new Event("input"));
  }
  if (outputEl && srcText) {
    outputEl.textContent     = "";
    outputEl.dataset.translatedText = "";
    document.getElementById("btnCopyTranslation").style.display = "none";
    document.getElementById("translatedCharCount").textContent  = "";
  }
});

document.getElementById("btnTranslate")?.addEventListener("click", handleTranslateText);

async function handleTranslateText() {
  if (!sourceTextEl) return;
  const text = sourceTextEl.value.trim();
  if (!text) return;

  const srcLang = sourceLangEl?.value || "auto";
  const tgtLang = targetLangEl?.value || "ne";

  const btn      = document.getElementById("btnTranslate");
  const outputEl = document.getElementById("translationOutput");

  btn.disabled      = true;
  btn.textContent   = "Translating...";
  outputEl.innerHTML = `<span class="output-placeholder">Translating...</span>`;
  hideTranslateError();

  try {
    const response = await fetch(`${STATE.apiBase}/api/translate/text`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text:            text,
        source_language: srcLang,
        target_language: tgtLang,
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Translation failed");
    }

    const data = await response.json();
    outputEl.textContent           = data.translated_text;
    outputEl.dataset.translatedText = data.translated_text;

    const charCount = document.getElementById("translatedCharCount");
    if (charCount) charCount.textContent = `${data.char_count} chars`;

    const copyBtn = document.getElementById("btnCopyTranslation");
    if (copyBtn) copyBtn.style.display = "inline-flex";

  } catch (err) {
    console.error("[Translator] Text error:", err);
    showTranslateError(err.message || "Translation failed. Please try again.");
    outputEl.innerHTML = `<span class="output-placeholder">Translation will appear here...</span>`;
  } finally {
    btn.disabled    = false;
    btn.textContent = "🌐 Translate";
  }
}

window.clearSourceText = function() {
  if (sourceTextEl) {
    sourceTextEl.value = "";
    sourceTextEl.dispatchEvent(new Event("input"));
  }
  const outputEl = document.getElementById("translationOutput");
  if (outputEl) {
    outputEl.innerHTML = `<span class="output-placeholder">Translation will appear here...</span>`;
    outputEl.dataset.translatedText = "";
  }
  const charCount = document.getElementById("translatedCharCount");
  if (charCount) charCount.textContent = "";
  const copyBtn = document.getElementById("btnCopyTranslation");
  if (copyBtn) copyBtn.style.display = "none";
  hideTranslateError();
};

window.copyTranslation = function() {
  const outputEl = document.getElementById("translationOutput");
  const text = outputEl?.dataset.translatedText || outputEl?.textContent || "";
  if (text) {
    navigator.clipboard.writeText(text).then(() => {
      const copyBtn = document.getElementById("btnCopyTranslation");
      if (copyBtn) {
        const orig = copyBtn.textContent;
        copyBtn.textContent = "✓ Copied!";
        setTimeout(() => { copyBtn.textContent = orig; }, 1500);
      }
    });
  }
};

function showTranslateError(msg) {
  const el = document.getElementById("translateError");
  const msgEl = document.getElementById("translateErrorMsg");
  if (el)  el.style.display  = "flex";
  if (msgEl) msgEl.textContent = msg;
}
function hideTranslateError() {
  const el = document.getElementById("translateError");
  if (el) el.style.display = "none";
}
window.hideTranslateError = hideTranslateError;

// ===================== DOCUMENT / IMAGE TRANSLATOR =====================

const docFileInput = document.getElementById("docFileInput");
const docDropZone  = document.getElementById("docDropZone");
const btnDocBrowse = document.getElementById("btnDocBrowse");

if (btnDocBrowse && docFileInput) btnDocBrowse.addEventListener("click", () => docFileInput.click());

if (docFileInput) {
  docFileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) handleDocumentTranslate(file);
    docFileInput.value = "";
  });
}

if (docDropZone) {
  docDropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    docDropZone.classList.add("drag-over");
  });
  docDropZone.addEventListener("dragleave", () => docDropZone.classList.remove("drag-over"));
  docDropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    docDropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) handleDocumentTranslate(file);
  });
}

async function handleDocumentTranslate(file) {
  const MAX_MB = 10;
  if (file.size > MAX_MB * 1024 * 1024) {
    showDocError(`File too large (${(file.size/1024/1024).toFixed(1)}MB). Max: ${MAX_MB}MB`);
    return;
  }

  const tgtLang  = document.getElementById("docTargetLang")?.value || "ne";
  const dropZoneEl  = document.getElementById("docDropZone");
  const progressEl  = document.getElementById("docProgress");
  const progressFil = document.getElementById("docProgressFill");
  const progressLbl = document.getElementById("docProgressLabel");
  const resultsEl   = document.getElementById("docResults");

  hideDocError();
  if (dropZoneEl) dropZoneEl.style.display = "none";
  if (progressEl) progressEl.style.display = "block";
  if (resultsEl)  resultsEl.style.display  = "none";

  let prog = 0;
  const interval = setInterval(() => {
    prog = Math.min(prog + Math.random() * 6, 80);
    if (progressFil) progressFil.style.width = `${prog}%`;
  }, 300);

  if (progressLbl) progressLbl.textContent = `Processing '${file.name}'...`;

  try {
    const formData = new FormData();
    formData.append("file",            file);
    formData.append("target_language", tgtLang);
    formData.append("source_language", "auto");

    const response = await fetch(`${STATE.apiBase}/api/translate/document`, {
      method: "POST",
      body:   formData,
    });

    clearInterval(interval);

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Document translation failed");
    }

    const data = await response.json();

    if (progressFil) progressFil.style.width = "100%";
    if (progressLbl) progressLbl.textContent = "✓ Done!";

    setTimeout(() => {
      if (progressEl) progressEl.style.display = "none";

      const origEl      = document.getElementById("docOriginalText");
      const transEl     = document.getElementById("docTranslatedText");
      const filenameEl  = document.getElementById("docResultFilename");

      if (origEl)     origEl.textContent    = data.original_text   || "—";
      if (transEl)    transEl.textContent   = data.translated_text || "—";
      if (filenameEl) filenameEl.textContent = `📄 ${data.filename}${data.page_count ? ` (${data.page_count} pages)` : ""}`;

      if (resultsEl) resultsEl.style.display = "block";
    }, 500);

  } catch (err) {
    clearInterval(interval);
    if (progressEl) progressEl.style.display = "none";
    if (dropZoneEl) dropZoneEl.style.display = "flex";
    if (progressFil) progressFil.style.width = "0%";
    showDocError(err.message || "Document translation failed. Please try again.");
    console.error("[DocTranslate] Error:", err);
  }
}

window.resetDocTranslator = function() {
  const dropZoneEl = document.getElementById("docDropZone");
  const resultsEl  = document.getElementById("docResults");
  if (dropZoneEl) dropZoneEl.style.display = "flex";
  if (resultsEl)  resultsEl.style.display  = "none";
  hideDocError();
};

window.copyDocTranslation = function() {
  const transEl = document.getElementById("docTranslatedText");
  const text = transEl?.textContent || "";
  if (text) {
    navigator.clipboard.writeText(text).then(() => {
      const btn = document.querySelector(".btn-copy-doc");
      if (btn) {
        const orig = btn.textContent;
        btn.textContent = "✓ Copied!";
        setTimeout(() => { btn.textContent = orig; }, 1500);
      }
    });
  }
};

function showDocError(msg) {
  const el    = document.getElementById("docTranslateError");
  const msgEl = document.getElementById("docTranslateErrorMsg");
  if (el)    el.style.display  = "flex";
  if (msgEl) msgEl.textContent = msg;
}
function hideDocError() {
  const el = document.getElementById("docTranslateError");
  if (el) el.style.display = "none";
}
window.hideDocError = hideDocError;

// ===================== EXPOSE GLOBALS =====================
window.loadPastSession    = loadPastSession;
window.deleteHistoryItem  = deleteHistoryItem;
window.removeDocument     = removeDocument;

// ===================== INITIALIZATION =====================

function init() {
  console.log("[Init] Nepali Chatbot + Translator UI initializing...");
  loadSession();
  bindChipEvents();
  loadSessionHistory();
  loadRAGStatus();
  DOM.messageInput.focus();
}

init();
