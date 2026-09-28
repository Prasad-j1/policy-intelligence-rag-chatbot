/* ==========================================================================
   API.JS — Policy Intelligence Assistant (AstraNova Technologies)
   Shared fetch wrapper for the FastAPI backend. Every page includes this
   via <script src="shared/api.js"></script> and calls functions on the
   global `PolicyAPI` object — no page should ever write a raw fetch()
   call to our backend directly. This is what keeps endpoint URLs,
   error handling, and response shapes consistent everywhere, the same
   way _shared.py keeps logic consistent on the backend.

   No ES modules on purpose — this project has no build step, and plain
   <script> tags avoid module-loading quirks (CORS-on-file://, MIME type
   issues) that trip people up on simple static-file setups.
   ========================================================================== */

const PolicyAPI = (() => {

  /* ------------------------------------------------------------------------
     CONFIG
     Change this one value if the backend ever runs on a different host/port
     (e.g. deployment). Nothing else in this file, or any page, should
     hardcode a URL.
     ------------------------------------------------------------------------ */
  const BASE_URL = "http://127.0.0.1:8000";


  /* ------------------------------------------------------------------------
     ERROR TYPE
     A single, predictable error shape every caller can rely on —
     pages check `error.status` / `error.detail` instead of guessing
     what shape a failed fetch() might have thrown.
     ------------------------------------------------------------------------ */
  class APIError extends Error {
    constructor(message, status, detail) {
      super(message);
      this.name = "APIError";
      this.status = status;     // HTTP status code, or 0 for network failures
      this.detail = detail;     // the backend's { "detail": "..." } message, if any
    }
  }


  /* ------------------------------------------------------------------------
     CORE REQUEST HELPER
     Every function below funnels through this. Handles JSON encoding,
     JSON parsing, and turning FastAPI's error responses into a clean
     APIError — so no page ever has to write try/catch fetch boilerplate.
     ------------------------------------------------------------------------ */
  async function request(path, { method = "GET", body = null, isFormData = false } = {}) {
    const url = `${BASE_URL}${path}`;

    const options = { method, headers: {} };

    if (body !== null) {
      if (isFormData) {
        // Let the browser set the multipart boundary header itself —
        // manually setting Content-Type for FormData breaks uploads.
        options.body = body;
      } else {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
      }
    }

    let response;
    try {
      response = await fetch(url, options);
    } catch (networkError) {
      // fetch() itself throws only on network failure (server down,
      // no internet, CORS block) — not on 4xx/5xx responses.
      throw new APIError("Could not reach the server. Is the backend running?", 0, null);
    }

    // Some endpoints (export) return raw file bytes, not JSON — those
    // callers handle the response object directly and never reach here.
    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json().catch(() => null);
    }

    if (!response.ok) {
      const detail = data && data.detail ? data.detail : `Request failed (${response.status})`;
      throw new APIError(detail, response.status, data ? data.detail : null);
    }

    return data;
  }


  /* ==========================================================================
     SYSTEM STATUS
     ========================================================================== */

  /**
   * Pings the backend's health-check endpoint. Used by the landing page's
   * live status indicator — never mock this, always reflect the real
   * server state.
   * @returns {Promise<boolean>} true if the backend responded successfully
   */
  async function checkHealth() {
    try {
      await request("/");
      return true;
    } catch (err) {
      return false;
    }
  }


  /* ==========================================================================
     POLICY ASSISTANT
     ========================================================================== */

  /**
   * Sends a question to the Policy Assistant workspace.
   * @param {string} question
   * @param {string|null} conversationId - omit/null to start a new conversation
   * @param {string} provider - the LLM provider to use
   * @returns {Promise<object>} ChatResponse shape from the backend
   */
  function askPolicy(question, conversationId = null,provider = "ollama") {
    return request("/policy/ask", {
      method: "POST",
      body: { question, conversation_id: conversationId, provider: provider}
    });
  }
  
  /**
   * Returns the curated starter questions for the Policy Assistant.
   * @returns {Promise<{workspace: string, questions: string[]}>}
   */
  function getPolicySuggestedQuestions() {
    return request("/policy/suggested-questions");
  }


  /* ==========================================================================
     PDF CHAT
     ========================================================================== */

  /**
   * Uploads a PDF and builds its temporary session index.
   * @param {File} file - a File object from an <input type="file"> or drop event
   * @returns {Promise<{session_id, filename, chunk_count, message}>}
   */
  function uploadPdf(file) {
    const formData = new FormData();
    formData.append("file", file);

    return request("/pdf_chat/upload", {
      method: "POST",
      body: formData,
      isFormData: true
    });
  }

  function streamPolicyAnswer(body, onToken, onDone, onError) {

    return new Promise(function (resolve, reject) {

        fetch(BASE_URL  + "/policy/stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        })

        .then(function (response) {

            if (!response.ok)
                throw new Error("Streaming request failed.");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            let buffer = "";

            function pump() {

                reader.read().then(function ({ done, value }) {

                    if (done) {
                        resolve();
                        return;
                    }

                    buffer += decoder.decode(value, { stream: true });

                    const events = buffer.split("\n\n");
                    buffer = events.pop();

                    events.forEach(function (event) {

                        if (!event.startsWith("data:"))
                            return;

                        const json = JSON.parse(event.replace("data:", "").trim());

                        console.log("SSE JSON =", json);

                        if (json.type === "token") {

                            onToken(json.content);

                        } else if (json.type === "done") {

                            onDone(json);

                            resolve();

                        } else if (json.type === "error") {

                            onError(json.message);

                            reject(json.message);

                        }

                    });

                    pump();

                });

            }

            pump();

        })

        .catch(function (err) {

            onError(err.message);

            reject(err);

        });

    });

}

  /**
   * Sends a question to the PDF Chat workspace. Requires a session_id
   * from a prior uploadPdf() call.
   * @param {string} question
   * @param {string} sessionId
   * @param {string|null} conversationId
   * @returns {Promise<object>} ChatResponse shape from the backend
   */
  function askPdf(question, sessionId, conversationId = null,provider = "ollama") {
    return request("/pdf_chat/ask", {
      method: "POST",
      body: { question, session_id: sessionId, conversation_id: conversationId, provider: provider }
    });
  }

  /**
   * Ends a PDF Chat session — deletes its temporary index from memory.
   * Matches the "Clear Workspace" button.
   * @param {string} sessionId
   */
  function clearPdfSession(sessionId) {
    return request(`/pdf_chat/clear/${encodeURIComponent(sessionId)}`, { method: "POST" });
  }

  /**
   * Returns generic starter questions for the PDF Chat workspace.
   * @returns {Promise<{workspace: string, questions: string[]}>}
   */
  function getPdfSuggestedQuestions() {
    return request("/pdf_chat/suggested-questions");
  }


  /* ==========================================================================
     CHAT HISTORY
     ========================================================================== */

  /**
   * Lists all conversations, optionally filtered by workspace.
   * @param {string|null} workspace - "policy", "pdf_chat", or null for all
   * @returns {Promise<Array>} ConversationSummary[]
   */
  function listConversations(workspace = null) {
    const query = workspace ? `?workspace=${encodeURIComponent(workspace)}` : "";
    return request(`/chat/conversations${query}`);
  }

  /**
   * Searches conversations by title (case-insensitive partial match).
   * @param {string} searchTerm
   * @returns {Promise<Array>} ConversationSummary[]
   */
  function searchConversations(searchTerm) {
    return request(`/chat/conversations/search?q=${encodeURIComponent(searchTerm)}`);
  }

  /**
   * Fetches a full conversation, including every message and its evidence.
   * @param {string} conversationId
   * @returns {Promise<object>} ConversationDetail shape
   */
  function getConversation(conversationId) {
    return request(`/chat/conversations/${encodeURIComponent(conversationId)}`);
  }

  /**
   * Deletes a conversation and all its messages/feedback.
   * @param {string} conversationId
   */
  function deleteConversation(conversationId) {
    return request(`/chat/conversations/${encodeURIComponent(conversationId)}`, { method: "DELETE" });
  }


  /* ==========================================================================
     FEEDBACK
     ========================================================================== */

  /**
   * Submits or updates 👍/👎 feedback on a specific assistant message.
   * @param {string} messageId
   * @param {boolean} isHelpful
   */
  function submitFeedback(messageId, isHelpful) {
    return request("/feedback/", {
      method: "POST",
      body: { message_id: messageId, is_helpful: isHelpful }
    });
  }

  /**
   * Fetches existing feedback for a message, if any — lets the UI show
   * which button (👍/👎) should already appear selected.
   * Returns null instead of throwing on 404, since "no feedback yet"
   * is an expected, normal state, not an error the caller should handle.
   * @param {string} messageId
   */
  async function getFeedback(messageId) {
    try {
      return await request(`/feedback/${encodeURIComponent(messageId)}`);
    } catch (err) {
      if (err instanceof APIError && err.status === 404) return null;
      throw err;
    }
  }


  /* ==========================================================================
     EXPORT
     Export returns raw file bytes, not JSON — this function triggers an
     actual browser download rather than returning data to the caller.
     ========================================================================== */

  /**
   * Downloads a conversation as a file. Triggers the browser's native
   * download prompt — no return value, the file just starts downloading.
   * @param {string} conversationId
   * @param {"txt"|"md"|"pdf"} format
   */
  async function exportConversation(conversationId, format) {
    const url = `${BASE_URL}/export/${encodeURIComponent(conversationId)}/${format}`;

    let response;
    try {
      response = await fetch(url);
    } catch (networkError) {
      throw new APIError("Could not reach the server to export.", 0, null);
    }

    if (!response.ok) {
      const data = await response.json().catch(() => null);
      const detail = data && data.detail ? data.detail : `Export failed (${response.status})`;
      throw new APIError(detail, response.status, detail);
    }

    // Extract the filename the backend chose (from Content-Disposition),
    // falling back to a generic name if parsing fails for any reason.
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="(.+)"/);
    const filename = match ? match[1] : `conversation.${format}`;

    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
  }


  /* ------------------------------------------------------------------------
     PUBLIC API
     ------------------------------------------------------------------------ */
  return {
    APIError,
    checkHealth,
    askPolicy,
    getPolicySuggestedQuestions,
    uploadPdf,
    streamPolicyAnswer: streamPolicyAnswer,
    askPdf,
    clearPdfSession,
    getPdfSuggestedQuestions,
    listConversations,
    searchConversations,
    getConversation,
    deleteConversation,
    submitFeedback,
    getFeedback,
    exportConversation
  };

})();

// async function streamPolicyAnswer(payload, onToken, onDone, onError) {

//     const response = await fetch("/policy/stream", {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json"
//         },
//         body: JSON.stringify(payload)
//     });

//     if (!response.ok) {
//         throw new Error("Streaming request failed.");
//     }

//     const reader = response.body.getReader();

//     const decoder = new TextDecoder();

//     let buffer = "";

//     while (true) {

//         const { done, value } = await reader.read();

//         if (done)
//             break;

//         buffer += decoder.decode(value, { stream: true });

//         const events = buffer.split("\n\n");

//         buffer = events.pop();

//         for (const event of events) {

//             if (!event.startsWith("data:"))
//                 continue;

//             const json = event.replace("data:", "").trim();

//             if (!json)
//                 continue;

//             const data = JSON.parse(json);

//             if (data.type === "token") {

//                 onToken(data.content);

//             }

//             else if (data.type === "done") {

//                 onDone(data);

//             }

//             else if (data.type === "error") {

//                 onError(data.message);

//             }

//         }

//     }

// }

// function streamPolicyAnswer(body, onToken, onDone, onError) {

//     return new Promise(function (resolve, reject) {

//         fetch(API_BASE + "/policy/stream", {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json"
//             },
//             body: JSON.stringify(body)
//         })

//         .then(function (response) {

//             if (!response.ok)
//                 throw new Error("Streaming request failed.");

//             const reader = response.body.getReader();
//             const decoder = new TextDecoder();

//             let buffer = "";

//             function pump() {

//                 reader.read().then(function ({ done, value }) {

//                     if (done) {
//                         resolve();
//                         return;
//                     }

//                     buffer += decoder.decode(value, { stream: true });

//                     const events = buffer.split("\n\n");
//                     buffer = events.pop();

//                     events.forEach(function (event) {

//                         if (!event.startsWith("data:"))
//                             return;

//                         const json = JSON.parse(
//                             event.replace("data:", "").trim()
//                         );

//                         if (json.type === "token") {

//                             onToken(json.content);

//                         } else if (json.type === "done") {

//                             onDone(json);

//                             resolve();

//                         } else if (json.type === "error") {

//                             onError(json.message);

//                             reject(json.message);

//                         }

//                     });

//                     pump();

//                 });

//             }

//             pump();

//         })

//         .catch(function (err) {

//             onError(err.message);

//             reject(err);

//         });

//     });

// }