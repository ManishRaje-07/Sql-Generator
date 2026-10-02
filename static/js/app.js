document.addEventListener("DOMContentLoaded", () => {
  let currentLang = "auto";
  let lastResult = null;

  const queryInput = document.getElementById("queryInput");
  const generateBtn = document.getElementById("generateBtn");
  const langBtns = document.querySelectorAll(".lang-btn");

  const errorBox = document.getElementById("errorBox");
  const errorMsg = document.getElementById("errorMsg");

  const sqlSection = document.getElementById("sqlSection");
  const sqlCode = document.getElementById("sqlCode");
  const langBadge = document.getElementById("langBadge");
  const copySqlBtn = document.getElementById("copySqlBtn");
  const sqlMeta = document.getElementById("sqlMeta");
  const nlpBody = document.getElementById("nlpBody");

  /* ── Language toggle ───────────────────────────── */
  langBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      langBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentLang = btn.dataset.lang;
    });
  });

  /* ── Generate SQL ──────────────────────────────── */
  async function run() {
    const query = queryInput.value.trim();
    if (!query) {
      queryInput.focus();
      return;
    }

    errorBox.style.display = "none";
    generateBtn.disabled = true;
    generateBtn.textContent = "Generating…";

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, language: currentLang }),
      });
      const data = await res.json();
      lastResult = data;

      /* Error from pipeline (e.g. DDL intent, unsafe SQL) */
      if (!res.ok || !data.success || !data.sql?.query) {
        showError(data.error);
        return;
      }

      renderSQL(data);
    } catch (e) {
      showError("Server request failed. Make sure the server is running.");
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "Generate SQL";
    }
  }

  function showError(msg) {
    errorMsg.textContent = msg;
    errorBox.style.display = "block";
    sqlSection.style.display = "none";
  }

  function renderSQL(data) {
    errorBox.style.display = "none";
    sqlSection.style.display = "block";

    sqlCode.textContent = data.sql.formatted || data.sql.query;

    const lang = data.language;
    langBadge.textContent = `${lang.name} • ${Math.round(lang.confidence * 100)}% confidence`;

    const intent = data.intent;
    sqlMeta.textContent = intent
      ? `Table: ${intent.target_table}  |  Intent: ${intent.action_type}  |  Latency: ${data.total_latency_ms} ms`
      : `SQL generated without database access  |  Latency: ${data.total_latency_ms} ms`;

    const nlp = data.nlp_breakdown;
    nlpBody.textContent = [
      `Language detected: ${lang.name} (${lang.detected_by.replace(/_/g, " ")})`,
      `Translated query: ${data.translation.translated_query}`,
      `Tokens: ${nlp.filtered_tokens.join(", ")}`,
      intent
        ? `Reasoning: ${intent.reasoning.join("; ")}`
        : "Generated as a SQL statement without database access.",
    ].join("\n");
  }

  /* ── Copy SQL ──────────────────────────────────── */
  copySqlBtn.addEventListener("click", () => {
    if (!lastResult?.sql) return;
    navigator.clipboard.writeText(lastResult.sql.query).then(() => {
      copySqlBtn.textContent = "Copied!";
      setTimeout(() => (copySqlBtn.textContent = "Copy"), 1800);
    });
  });

  /* ── Keyboard shortcut ─────────────────────────── */
  queryInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      run();
    }
  });

  generateBtn.addEventListener("click", run);
});
