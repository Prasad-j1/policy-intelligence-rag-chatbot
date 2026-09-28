/* ==========================================================================
   UI.JS — Policy Intelligence Assistant (AstraNova Technologies)
   Shared UI utilities used identically by policy_assistant_workspace.html
   and pdf_chat_workspace.html — toasts, markdown rendering, confirmation
   dialogs, and conversation-history grouping. Same reasoning as
   backend/api/_shared.py: logic two pages both need lives in exactly
   one place, not two independently-editable copies.
   ========================================================================== */

const PolicyUI = (() => {

  /* ==========================================================================
     TOASTS
     ========================================================================== */
  let toastContainer = null;

  function ensureToastContainer() {
    if (toastContainer) return toastContainer;
    toastContainer = document.createElement("div");
    toastContainer.className = "pia-toast-container";
    toastContainer.setAttribute("role", "status");
    toastContainer.setAttribute("aria-live", "polite");
    document.body.appendChild(toastContainer);
    return toastContainer;
  }

  /**
   * Shows a stacked, auto-dismissing toast notification.
   * @param {string} message
   * @param {"success"|"error"|"info"} type
   * @param {number} duration - ms before auto-dismiss
   */
  function toast(message, type = "info", duration = 4000) {
    const container = ensureToastContainer();

    const el = document.createElement("div");
    el.className = `pia-toast pia-toast-${type}`;
    el.textContent = message;

    container.appendChild(el);
    requestAnimationFrame(() => el.classList.add("in"));

    const remove = () => {
      el.classList.remove("in");
      el.addEventListener("transitionend", () => el.remove(), { once: true });
    };

    const timer = setTimeout(remove, duration);
    el.addEventListener("click", () => { clearTimeout(timer); remove(); });
  }


  /* ==========================================================================
     CONFIRM DIALOG
     Replaces native confirm() with a styled modal matching the app's
     visual language, per the "proper confirmation dialogs" requirement.
     ========================================================================== */

  /**
   * @param {{title: string, message: string, confirmLabel?: string, danger?: boolean}} opts
   * @returns {Promise<boolean>}
   */
  function confirmDialog({ title, message, confirmLabel = "Confirm", danger = false }) {
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.className = "pia-modal-overlay";

      overlay.innerHTML = `
        <div class="pia-modal glass" role="alertdialog" aria-modal="true" aria-labelledby="pia-modal-title">
          <h3 id="pia-modal-title">${escapeHtml(title)}</h3>
          <p>${escapeHtml(message)}</p>
          <div class="pia-modal-actions">
            <button class="btn btn-secondary" data-action="cancel">Cancel</button>
            <button class="btn ${danger ? "btn-danger" : "btn-primary"}" data-action="confirm">${escapeHtml(confirmLabel)}</button>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);
      document.body.style.overflow = "hidden";
      requestAnimationFrame(() => overlay.classList.add("in"));

      const cleanup = (result) => {
        overlay.classList.remove("in");
        document.body.style.overflow = "";
        overlay.addEventListener("transitionend", () => overlay.remove(), { once: true });
        resolve(result);
      };

      overlay.querySelector('[data-action="confirm"]').addEventListener("click", () => cleanup(true));
      overlay.querySelector('[data-action="cancel"]').addEventListener("click", () => cleanup(false));
      overlay.addEventListener("click", (e) => { if (e.target === overlay) cleanup(false); });

      document.addEventListener("keydown", function escHandler(e) {
        if (e.key === "Escape") {
          cleanup(false);
          document.removeEventListener("keydown", escHandler);
        }
      });
    });
  }


  /* ==========================================================================
     MARKDOWN RENDERING
     A deliberately small, pragmatic subset (bold, italic, inline code,
     code blocks, lists, headers, simple pipe tables) — not a full
     CommonMark implementation. Covers what grounded policy answers
     realistically contain. HTML is escaped FIRST, always, before any
     markdown transform runs — this is what makes it safe to render
     LLM output directly without risking script injection.
     ========================================================================== */

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function renderMarkdown(raw) {
    let text = escapeHtml(raw);

    // Fenced code blocks first (```...```), so their content is never
    // touched by later inline rules (bold/italic inside code would be wrong).
    text = text.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code.trim()}</code></pre>`);

    // Simple pipe tables: header row, separator row, body rows.
    text = text.replace(
      /((?:^\|.+\|$\n?)+)/gm,
      (block) => {
        const rows = block.trim().split("\n").filter(Boolean);
        if (rows.length < 2 || !/^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$/.test(rows[1])) return block;

        const toCells = (row) => row.replace(/^\||\|$/g, "").split("|").map(c => c.trim());
        const header = toCells(rows[0]);
        const body = rows.slice(2).map(toCells);

        let html = "<table><thead><tr>";
        header.forEach(h => html += `<th>${h}</th>`);
        html += "</tr></thead><tbody>";
        body.forEach(r => {
          html += "<tr>";
          r.forEach(c => html += `<td>${c}</td>`);
          html += "</tr>";
        });
        html += "</tbody></table>";
        return html;
      }
    );

    // Headers (### -> h4, ## -> h3, # -> h2) — capped so they never
    // outrank the page's own heading hierarchy.
    text = text.replace(/^### (.+)$/gm, "<h4>$1</h4>");
    text = text.replace(/^## (.+)$/gm, "<h3>$1</h3>");
    text = text.replace(/^# (.+)$/gm, "<h2>$1</h2>");

    // Inline code, bold, italic
    text = text.replace(/`([^`]+)`/g, "<code>$1</code>");
    text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    text = text.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, "<em>$1</em>");

    // Unordered / ordered lists — group consecutive list lines into one <ul>/<ol>
    text = text.replace(/((?:^[-*] .+$\n?)+)/gm, (block) => {
      const items = block.trim().split("\n").map(l => `<li>${l.replace(/^[-*] /, "")}</li>`).join("");
      return `<ul>${items}</ul>`;
    });
    text = text.replace(/((?:^\d+\. .+$\n?)+)/gm, (block) => {
      const items = block.trim().split("\n").map(l => `<li>${l.replace(/^\d+\. /, "")}</li>`).join("");
      return `<ol>${items}</ol>`;
    });

    // Paragraphs: remaining double-newline-separated blocks become <p>,
    // single newlines within a block become <br>. Skip blocks that are
    // already block-level HTML from the transforms above.
    text = text
      .split(/\n\n+/)
      .map(block => {
        const trimmed = block.trim();
        if (!trimmed) return "";
        if (/^<(h2|h3|h4|ul|ol|table|pre)/.test(trimmed)) return trimmed;
        return `<p>${trimmed.replace(/\n/g, "<br>")}</p>`;
      })
      .join("");

    return text;
  }


  /* ==========================================================================
     CONVERSATION GROUPING
     Buckets a ConversationSummary[] into Today / Yesterday / Previous 7
     Days / Previous 30 Days / Older, for the sidebar history list.
     Assumes the array is already sorted newest-first (the backend's
     list_conversations already orders by updated_at desc).
     ========================================================================== */

  function groupByRecency(conversations) {
    const groups = { "Today": [], "Yesterday": [], "Previous 7 Days": [], "Previous 30 Days": [], "Older": [] };

    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfYesterday = new Date(startOfToday);
    startOfYesterday.setDate(startOfYesterday.getDate() - 1);
    const sevenDaysAgo = new Date(startOfToday);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    const thirtyDaysAgo = new Date(startOfToday);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

    conversations.forEach(conv => {
      const updated = new Date(conv.updated_at);
      if (updated >= startOfToday) groups["Today"].push(conv);
      else if (updated >= startOfYesterday) groups["Yesterday"].push(conv);
      else if (updated >= sevenDaysAgo) groups["Previous 7 Days"].push(conv);
      else if (updated >= thirtyDaysAgo) groups["Previous 30 Days"].push(conv);
      else groups["Older"].push(conv);
    });

    return groups;
  }


  /* ==========================================================================
     MISC HELPERS
     ========================================================================== */

  function debounce(fn, wait = 250) {
    let timer;
    return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => fn(...args), wait);
    };
  }

  function formatTime(isoString) {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  /**
   * Copies text to the clipboard, with a toast confirming success/failure.
   * Centralized here so every "Copy" / "Copy Citation" button behaves
   * identically across both workspace pages.
   */
  async function copyToClipboard(text, successMessage = "Copied to clipboard") {
    try {
      await navigator.clipboard.writeText(text);
      toast(successMessage, "success", 2000);
    } catch (err) {
      toast("Could not copy to clipboard", "error");
    }
  }


  return {
    toast,
    confirmDialog,
    escapeHtml,
    renderMarkdown,
    groupByRecency,
    debounce,
    formatTime,
    copyToClipboard
  };

})();