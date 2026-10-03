(function () {
  function $(id) {
    return document.getElementById(id);
  }

  const state = {
    threadId: null,
    chatInFlight: false,
  };

  function setThreadPill() {
    const text = state.threadId ? `thread_id: ${state.threadId}` : "No active thread";
    const pill = $("threadPill");
    if (pill) pill.textContent = text;
    const uploadPill = $("uploadThreadPill");
    if (uploadPill) {
      uploadPill.textContent = state.threadId
        ? text
        : "No active thread — one will be created on upload";
    }
  }

  async function refreshPublicConfig() {
    const dot = $("keyStatusDot");
    const label = $("keyStatusText");
    const base = $("ragBaseLabel");
    try {
      const res = await fetch("/api/config/public");
      const data = await res.json();
      if (base) base.textContent = data.fileflow_api_base || "—";
      const ok = data.api_key_configured;
      if (dot) {
        dot.classList.toggle("on", ok);
        dot.classList.toggle("off", !ok);
      }
      if (label) {
        label.textContent = ok ? "API key configured (server)" : "Set FILEFLOW_API_KEY or server config";
      }
    } catch {
      if (base) base.textContent = "—";
      if (label) label.textContent = "Could not load config";
    }
  }

  function clearEmptyState(box) {
    const empty = box.querySelector(".empty");
    if (empty) empty.remove();
  }

  function scrollMessagesToEnd() {
    const box = $("messages");
    if (!box) return;
    box.scrollTop = box.scrollHeight;
  }

  function appendUserBubble(box, text) {
    const wrap = document.createElement("div");
    wrap.className = "msg-row user msg-row--pending";
    const bubble = document.createElement("div");
    bubble.className = "bubble user";
    bubble.textContent = text;
    wrap.appendChild(bubble);
    box.appendChild(wrap);
  }

  function appendTypingRow(box) {
    const wrap = document.createElement("div");
    wrap.className = "msg-row assistant msg-row--typing";
    wrap.dataset.role = "typing";
    wrap.setAttribute("aria-live", "polite");
    wrap.setAttribute("aria-label", "Assistant is replying");

    const av = document.createElement("div");
    av.className = "msg-avatar";
    av.setAttribute("aria-hidden", "true");
    av.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/></svg>';

    const bubble = document.createElement("div");
    bubble.className = "bubble assistant bubble--typing";
    const typing = document.createElement("span");
    typing.className = "typing-indicator";
    typing.innerHTML = "<span></span><span></span><span></span>";
    bubble.appendChild(typing);
    wrap.appendChild(av);
    wrap.appendChild(bubble);
    box.appendChild(wrap);
    return wrap;
  }

  function removeTypingRow(box) {
    const row = box.querySelector('[data-role="typing"]');
    if (row) row.remove();
  }

  function appendAssistantBubble(box, html, isError) {
    const wrap = document.createElement("div");
    wrap.className = "msg-row assistant msg-row--typing";
    const av = document.createElement("div");
    av.className = "msg-avatar";
    av.setAttribute("aria-hidden", "true");
    av.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/></svg>';
    const bubble = document.createElement("div");
    bubble.className = isError ? "bubble assistant bubble--error" : "bubble assistant";
    bubble.innerHTML = isError ? escapeHtml(html).replace(/\n/g, "<br>") : html;
    wrap.appendChild(av);
    wrap.appendChild(bubble);
    box.appendChild(wrap);
  }

  function renderMessages(rows) {
    const box = $("messages");
    if (!box) return;
    box.innerHTML = "";
    if (!rows.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.innerHTML =
        "<strong>Welcome to the shop assistant</strong><br />Ask about your shelved documents. Upload new files on <strong>Upload to RAG</strong>.";
      box.appendChild(empty);
      return;
    }
    rows.forEach((row) => {
      const wrap = document.createElement("div");
      wrap.className = `msg-row ${row.role === "user" ? "user" : "assistant"}`;

      if (row.role === "assistant") {
        const av = document.createElement("div");
        av.className = "msg-avatar";
        av.setAttribute("aria-hidden", "true");
        av.innerHTML =
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.17L4 17.17V4h16v12z"/></svg>';
        const bubble = document.createElement("div");
        bubble.className = "bubble assistant";
        bubble.innerHTML = renderAssistantMarkdown(row.content || "");
        wrap.appendChild(av);
        wrap.appendChild(bubble);
      } else {
        const bubble = document.createElement("div");
        bubble.className = "bubble user";
        bubble.textContent = row.content;
        wrap.appendChild(bubble);
      }
      box.appendChild(wrap);
    });
    box.scrollTop = box.scrollHeight;
  }

  function renderAssistantMarkdown(text) {
    const raw = String(text || "");
    if (window.marked && window.DOMPurify) {
      const html = window.marked.parse(raw, { breaks: true, gfm: true });
      return window.DOMPurify.sanitize(html);
    }
    return escapeHtml(raw).replace(/\n/g, "<br>");
  }

  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, (ch) => {
      if (ch === "&") return "&amp;";
      if (ch === "<") return "&lt;";
      if (ch === ">") return "&gt;";
      if (ch === '"') return "&quot;";
      return "&#39;";
    });
  }

  async function loadMessages() {
    if (!state.threadId) {
      renderMessages([]);
      return;
    }
    const res = await fetch(`/api/chats/${encodeURIComponent(state.threadId)}/messages`);
    const data = await res.json();
    renderMessages(data.messages || []);
  }

  function truncatePreview(text, maxLen) {
    const t = String(text || "").replace(/\s+/g, " ").trim();
    if (t.length <= maxLen) return t;
    return `${t.slice(0, maxLen - 1)}…`;
  }

  function formatChatTime(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  async function refreshChatHistory() {
    const list = $("chatHistoryList");
    const countEl = $("chatHistoryCount");
    if (!list) return;
    try {
      const res = await fetch("/api/chats");
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();
      const chats = data.chats || [];
      if (countEl) {
        countEl.hidden = chats.length === 0;
        countEl.textContent = String(chats.length);
      }
      list.innerHTML = "";
      if (!chats.length) {
        const p = document.createElement("p");
        p.className = "chat-history-empty";
        p.textContent = "No conversations yet. Send a message or tap New chat.";
        list.appendChild(p);
        return;
      }
      chats.forEach((c) => {
        const row = document.createElement("div");
        row.className = "chat-history-row";
        row.setAttribute("role", "listitem");

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "chat-history-item";
        btn.dataset.threadId = c.thread_id;
        if (c.thread_id === state.threadId) btn.classList.add("is-active");

        const title = document.createElement("p");
        title.className = "chat-history-item-title";
        title.textContent = c.title && String(c.title).trim() ? c.title : "Untitled chat";

        const meta = document.createElement("p");
        meta.className = "chat-history-item-meta";
        meta.textContent = formatChatTime(c.updated_at) || "—";

        btn.appendChild(title);
        btn.appendChild(meta);

        if (c.last_message) {
          const prev = document.createElement("p");
          prev.className = "chat-history-item-preview";
          prev.textContent = truncatePreview(c.last_message, 100);
          btn.appendChild(prev);
        }

        const del = document.createElement("button");
        del.type = "button";
        del.className = "chat-history-delete";
        del.dataset.threadId = c.thread_id;
        del.setAttribute("aria-label", "Delete this conversation");
        del.title = "Delete";
        del.innerHTML =
          '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M10 11v6M14 11v6"/></svg>';

        row.appendChild(btn);
        row.appendChild(del);
        list.appendChild(row);
      });
    } catch {
      list.innerHTML = "";
      const p = document.createElement("p");
      p.className = "chat-history-empty";
      p.textContent = "Could not load conversations. Tap Refresh to try again.";
      list.appendChild(p);
      if (countEl) countEl.hidden = true;
    }
  }

  async function switchToThread(threadId) {
    if (!threadId || state.chatInFlight) return;
    state.threadId = threadId;
    setThreadPill();
    await loadMessages();
    await refreshChatHistory();
  }

  async function deleteChatById(threadId) {
    if (!threadId || state.chatInFlight) return;
    if (!window.confirm("Delete this conversation permanently? This cannot be undone.")) return;
    try {
      const res = await fetch(`/api/chats/${encodeURIComponent(threadId)}`, { method: "DELETE" });
      if (!res.ok) {
        let msg = "Could not delete chat.";
        try {
          const err = await res.json();
          if (err.detail) msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        } catch {
          /* ignore */
        }
        window.alert(msg);
        return;
      }
      if (state.threadId === threadId) {
        state.threadId = null;
        setThreadPill();
        renderMessages([]);
      }
      await refreshChatHistory();
    } catch (err) {
      window.alert(err && err.message ? err.message : "Could not delete chat.");
    }
  }

  async function createChat() {
    const res = await fetch("/api/chats", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "New chat" }),
    });
    const data = await res.json();
    if (!data.thread_id) return;
    state.threadId = data.thread_id;
    setThreadPill();
    await loadMessages();
    await refreshChatHistory();
  }

  function setComposerSending(sending) {
    const wrap = document.querySelector(".composer-wrap");
    const btn = $("btnSend");
    const input = $("msgInput");
    if (wrap) wrap.classList.toggle("is-sending", sending);
    if (btn) {
      btn.classList.toggle("is-loading", sending);
      btn.disabled = sending;
      btn.setAttribute("aria-busy", sending ? "true" : "false");
    }
    if (input) input.readOnly = sending;
  }

  function extractAssistantReply(data) {
    const p = data && data.parsed;
    if (p && typeof p.langgraph_response === "string" && p.langgraph_response.trim()) {
      return p.langgraph_response.trim();
    }
    return null;
  }

  function formatQueryFailure(data, res) {
    if (data && typeof data.detail === "string") return data.detail;
    if (data && data.detail && typeof data.detail === "object") {
      try {
        return JSON.stringify(data.detail);
      } catch {
        return "Request failed.";
      }
    }
    if (data && data.body && typeof data.body === "string") return `Upstream: ${data.body.slice(0, 400)}`;
    return `Request failed (${res.status}).`;
  }

  async function sendMessage() {
    const input = $("msgInput");
    const box = $("messages");
    if (!input || !box || state.chatInFlight) return;

    const text = input.value.trim();
    if (!text) return;

    state.chatInFlight = true;
    setComposerSending(true);
    const historyListEl = $("chatHistoryList");
    if (historyListEl) historyListEl.classList.add("is-busy");

    let typingRow = null;

    try {
      if (!state.threadId) {
        await createChat();
      }
      if (!state.threadId) {
        clearEmptyState(box);
        appendAssistantBubble(
          box,
          "Could not start a chat thread. Check your connection and try again.",
          true
        );
        scrollMessagesToEnd();
        return;
      }

      const payload = {
        query_text: text,
        top_k: 5,
        thread_id: state.threadId,
        history: true,
        persist: true,
      };

      clearEmptyState(box);
      appendUserBubble(box, text);
      typingRow = appendTypingRow(box);
      input.value = "";
      scrollMessagesToEnd();

      const res = await fetch("/api/rag/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      let data = null;
      try {
        data = await res.json();
      } catch {
        data = { ok: false, parsed: null };
      }

      const raw = $("rawOut");
      if (raw) raw.textContent = JSON.stringify(data, null, 2);

      removeTypingRow(box);

      const upstreamOk = res.ok && data && data.ok === true;
      const reply = upstreamOk ? extractAssistantReply(data) : null;

      if (upstreamOk && payload.persist && state.threadId) {
        await loadMessages();
      } else if (upstreamOk && reply) {
        appendAssistantBubble(box, renderAssistantMarkdown(reply), false);
      } else if (upstreamOk && !reply) {
        appendAssistantBubble(
          box,
          renderAssistantMarkdown(
            "The assistant returned no text in `langgraph_response`. Expand **Raw API output** below to inspect the payload."
          ),
          false
        );
      } else {
        appendAssistantBubble(box, formatQueryFailure(data, res), true);
      }

      scrollMessagesToEnd();
    } catch (err) {
      removeTypingRow(box);
      const msg = err && err.message ? err.message : String(err);
      appendAssistantBubble(box, `Could not reach the server.\n\n${msg}`, true);
      scrollMessagesToEnd();
    } finally {
      state.chatInFlight = false;
      setComposerSending(false);
      if (typingRow && typingRow.parentNode) typingRow.remove();
      scrollMessagesToEnd();
      const hl = $("chatHistoryList");
      if (hl) hl.classList.remove("is-busy");
      void refreshChatHistory();
    }
  }

  function initChatOverlay() {
    const overlay = $("chatOverlay");
    const fab = $("chatFab");
    const backdrop = $("chatBackdrop");
    const closeBtn = $("btnCloseChat");
    const heroOpen = $("heroOpenChat");

    function setOpen(open) {
      if (!overlay) return;
      overlay.classList.toggle("is-open", open);
      overlay.setAttribute("aria-hidden", open ? "false" : "true");
      document.body.classList.toggle("chat-open", open);
      if (fab) {
        fab.setAttribute("aria-expanded", open ? "true" : "false");
      }
      if (open) {
        void refreshChatHistory();
        const input = $("msgInput");
        if (input) setTimeout(() => input.focus(), 200);
      }
    }

    if (fab) {
      fab.addEventListener("click", () => setOpen(true));
    }
    if (backdrop) {
      backdrop.addEventListener("click", () => setOpen(false));
    }
    if (closeBtn) {
      closeBtn.addEventListener("click", () => setOpen(false));
    }
    if (heroOpen) {
      heroOpen.addEventListener("click", () => setOpen(true));
    }

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && overlay && overlay.classList.contains("is-open")) {
        setOpen(false);
      }
    });
  }

  function initChatHistory() {
    const list = $("chatHistoryList");
    const refreshBtn = $("btnRefreshChats");
    if (list) {
      list.addEventListener("click", (e) => {
        const delBtn = e.target.closest(".chat-history-delete");
        if (delBtn) {
          e.preventDefault();
          e.stopPropagation();
          const delId = delBtn.getAttribute("data-thread-id");
          if (delId) void deleteChatById(delId);
          return;
        }
        const item = e.target.closest(".chat-history-item[data-thread-id]");
        if (!item) return;
        const id = item.getAttribute("data-thread-id");
        if (id) void switchToThread(id);
      });
    }
    if (refreshBtn) {
      refreshBtn.addEventListener("click", (e) => {
        e.preventDefault();
        void refreshChatHistory();
      });
    }
  }

  function setUploadLoading(visible, filename) {
    const root = $("uploadLoadingRoot");
    const fileLabel = $("uploadLoadingFile");
    const card = document.querySelector(".upload-card");
    if (!root) return;
    root.classList.toggle("is-visible", visible);
    root.setAttribute("aria-hidden", visible ? "false" : "true");
    document.body.classList.toggle("upload-busy", visible);
    if (card) card.classList.toggle("is-busy", visible);
    if (fileLabel) {
      fileLabel.textContent = filename ? filename : "";
    }
  }

  function initUploadPage() {
    const fileInput = $("ragFileInput");
    const btn = $("btnRagUpload");
    const statusEl = $("uploadStatus");
    const raw = $("uploadRawOut");
    if (!fileInput || !btn) return;

    async function runUpload() {
      const file = fileInput.files[0];
      if (!file) {
        if (statusEl) {
          statusEl.textContent = "Choose a file first.";
          statusEl.classList.add("is-error");
        }
        return;
      }
      if (btn.disabled) return;

      if (!state.threadId) {
        await createChat();
      }

      if (statusEl) {
        statusEl.textContent = "";
        statusEl.classList.remove("is-error");
      }

      btn.disabled = true;
      fileInput.disabled = true;
      setUploadLoading(true, file.name);

      const fd = new FormData();
      fd.append("file", file);
      fd.append("thread_id", state.threadId);

      try {
        const res = await fetch("/api/rag/upload", { method: "POST", body: fd });
        let data = null;
        try {
          data = await res.json();
        } catch {
          data = { ok: false };
        }
        if (raw) raw.textContent = JSON.stringify(data, null, 2);
        if (statusEl) {
          if (data && data.ok) {
            statusEl.textContent = "Upload finished.";
            statusEl.classList.remove("is-error");
          } else {
            const detail =
              data && data.detail
                ? typeof data.detail === "string"
                  ? data.detail
                  : JSON.stringify(data.detail)
                : null;
            statusEl.textContent = detail || `Upload failed (${data && data.status ? data.status : res.status}).`;
            statusEl.classList.add("is-error");
          }
        }
        fileInput.value = "";
      } catch (err) {
        if (statusEl) {
          statusEl.textContent = String(err && err.message ? err.message : err);
          statusEl.classList.add("is-error");
        }
      } finally {
        btn.disabled = false;
        fileInput.disabled = false;
        setUploadLoading(false, "");
        void refreshChatHistory();
      }
    }

    btn.addEventListener("click", runUpload);
  }

  const newChatBtn = $("btnNewChat");
  if (newChatBtn) newChatBtn.addEventListener("click", createChat);

  const sendBtn = $("btnSend");
  if (sendBtn) sendBtn.addEventListener("click", sendMessage);

  const msgInput = $("msgInput");
  if (msgInput) {
    msgInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
  }

  initChatOverlay();
  initChatHistory();
  initUploadPage();

  refreshPublicConfig();
  setThreadPill();
  renderMessages([]);
  void refreshChatHistory();
})();
