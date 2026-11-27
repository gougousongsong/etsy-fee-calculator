/* Wires the CSV cleaner page to ./cleaner.js. No network calls anywhere. */
(function () {
  const $ = (id) => document.getElementById(id);
  const fileInput = $("file");
  const paste = $("paste");
  const out = $("out");
  let lastCsv = "";
  let lastName = "cleaned.csv";

  const SAMPLE = [
    "Order ID , Customer , Amount , Order Date ",
    '1001, Alice ,"$1,200.00", 04/03/2026 ',
    "1002,Bob,45.00,2026-03-05",
    ",,,",
    '1001, Alice ,"$1,200.00", 04/03/2026 ',
    "1003,Carol,not-a-number,13/13/2026",
    '1004,"Dave, Jr.",99.5,5 Mar 2026',
    '1005,Eve,"1.234,50",12 Mar 2025',
  ].join("\n");

  function options() {
    return {
      dedupe: $("optDedupe").checked,
      normaliseNumbers: $("optNumbers").checked,
      normaliseDates: $("optDates").checked,
    };
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function render(result) {
    const s = result.stats;
    $("stats").innerHTML = [
      `<span class="pill">rows in <b>${s.inputRows}</b></span>`,
      `<span class="pill good">kept <b>${s.kept}</b></span>`,
      `<span class="pill">empty dropped <b>${s.droppedEmpty}</b></span>`,
      `<span class="pill">duplicates dropped <b>${s.droppedDuplicate}</b></span>`,
      `<span class="pill ${s.flagged ? "warn" : "good"}">flagged <b>${s.flagged}</b></span>`,
    ].join("");

    const flagBox = $("flagBox");
    const flagBody = $("flagTable").querySelector("tbody");
    if (result.flags.length) {
      flagBox.hidden = false;
      flagBody.innerHTML = result.flags
        .slice(0, 200)
        .map(
          (f) =>
            `<tr><td class="mono">${f.line}</td><td>${escapeHtml(f.column)}</td>` +
            `<td class="mono">${escapeHtml(f.value)}</td><td>${escapeHtml(f.reason)}</td></tr>`,
        )
        .join("");
    } else {
      flagBox.hidden = true;
      flagBody.innerHTML = "";
    }

    const head = $("preview").querySelector("thead");
    const body = $("preview").querySelector("tbody");
    head.innerHTML = `<tr>${result.headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr>`;
    const shown = result.rows.slice(0, 12);
    body.innerHTML = shown
      .map((r) => `<tr>${r.map((c) => `<td class="mono">${escapeHtml(c)}</td>`).join("")}</tr>`)
      .join("");
    $("previewNote").textContent =
      result.rows.length > shown.length
        ? `Showing the first ${shown.length} of ${result.rows.length} clean rows — the download has all of them.`
        : `All ${result.rows.length} clean rows shown.`;

    lastCsv = result.csv;
    out.hidden = false;
    out.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function run(text, name) {
    if (!text || !text.trim()) {
      paste.focus();
      return;
    }
    if (name) lastName = name.replace(/\.(csv|txt)$/i, "") + "-cleaned.csv";
    render(window.cleanCsv(text, options()));
  }

  $("run").addEventListener("click", () => {
    // cleanCsv comes from cleaner.js, loaded before this file.
    const mod = window.cleanCsv ? { cleanCsv: window.cleanCsv } : null;
    if (!mod) {
      alert("The cleaner script did not load. Reload the page.");
      return;
    }
    run(paste.value, null);
  });

  $("sample").addEventListener("click", () => {
    paste.value = SAMPLE;
    run(SAMPLE, "sample.csv");
  });

  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      paste.value = String(reader.result || "");
      run(paste.value, file.name);
    };
    reader.onerror = () => alert("Could not read that file in the browser.");
    reader.readAsText(file);
  });

  $("download").addEventListener("click", () => {
    if (!lastCsv) return;
    const blob = new Blob([lastCsv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = lastName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  $("copy").addEventListener("click", async () => {
    if (!lastCsv) return;
    try {
      await navigator.clipboard.writeText(lastCsv);
      $("copy").textContent = "Copied";
      setTimeout(() => ($("copy").textContent = "Copy to clipboard"), 1500);
    } catch (e) {
      alert("Clipboard is blocked in this browser — use the download button.");
    }
  });
})();
