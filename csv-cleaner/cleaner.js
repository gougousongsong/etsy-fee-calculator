/**
 * CSV cleaner core — runs entirely in the browser, no upload, no network.
 * Exported for Node so the rules can be unit-tested outside the page.
 *
 * Rules (same as the paid done-for-you service):
 *  1. RFC4180-ish parse: quoted cells, embedded commas and newlines.
 *  2. Trim every cell.
 *  3. Drop rows that are entirely empty after trimming.
 *  4. Drop exact duplicate rows (first occurrence wins).
 *  5. Amount columns: "$1,234.50" / "1.234,50" / "(45.00)" -> plain decimal.
 *  6. Date columns: normalise to YYYY-MM-DD when the row says what day it means.
 *  7. Anything that cannot be converted is kept verbatim and *flagged*, never guessed.
 */

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  const src = text.replace(/^\uFEFF/, "");

  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (quoted) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          cell += '"';
          i++;
        } else {
          quoted = false;
        }
      } else {
        cell += ch;
      }
      continue;
    }
    if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      row.push(cell);
      cell = "";
    } else if (ch === "\n") {
      row.push(cell);
      rows.push(row);
      row = [];
      cell = "";
    } else if (ch === "\r") {
      // swallow; \r\n handled by the \n branch
    } else {
      cell += ch;
    }
  }
  if (cell.length || row.length) {
    row.push(cell);
    rows.push(row);
  }
  return rows;
}

function toCsv(rows) {
  return rows
    .map((r) =>
      r
        .map((v) => {
          const s = v == null ? "" : String(v);
          return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
        })
        .join(","),
    )
    .join("\n");
}

const AMOUNT_HINT = /(amount|total|price|cost|value|sum|paid|fee|balance|revenue)/i;
const DATE_HINT = /(date|day|when|created|updated|posted|due)/i;

/** "1,234.50" | "$1,234.50" | "(45.00)" | "1.234,50" -> number, or null. */
function parseAmount(raw) {
  let s = String(raw).trim();
  if (!s) return null;
  let negative = false;
  if (/^\(.*\)$/.test(s)) {
    negative = true;
    s = s.slice(1, -1).trim();
  }
  s = s.replace(/[$€£¥\s]/g, "");
  if (s.startsWith("-")) {
    negative = true;
    s = s.slice(1);
  } else if (s.endsWith("-")) {
    negative = true;
    s = s.slice(0, -1);
  }
  // European style "1.234,50" when the dot groups thousands and the comma is decimal.
  if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(s)) {
    s = s.replace(/\./g, "").replace(",", ".");
  } else if (s.includes(",") && !s.includes(".")) {
    // "1200,00" is a decimal comma; "1,200" is a thousands comma. Anything else is
    // ambiguous money, and ambiguous money gets flagged, never silently rescaled.
    if (/^\d+,\d{2}$/.test(s)) s = s.replace(",", ".");
    else if (/^\d{1,3}(,\d{3})+$/.test(s)) s = s.replace(/,/g, "");
    else return null;
  } else if (s.includes(",") && s.includes(".")) {
    // "1,200.00" is US: the comma groups thousands. Anything else with both
    // separators is ambiguous money and gets flagged instead of guessed.
    if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(s)) s = s.replace(/,/g, "");
    else return null;
  }
  if (!/^\d+(\.\d+)?$/.test(s)) return null;
  const value = Number(s);
  if (!Number.isFinite(value)) return null;
  return negative ? -value : value;
}

/** Only converts when the meaning is unambiguous; otherwise null. */
function parseDate(raw) {
  const s = String(raw).trim();
  if (!s) return null;
  const iso = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$/);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const us = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (us && Number(us[1]) <= 12) {
    return `${us[3]}-${us[1].padStart(2, "0")}-${us[2].padStart(2, "0")}`;
  }
  const dmy = s.match(/^(\d{1,2})[.\/-](\d{1,2})[.\/-](\d{4})$/);
  if (dmy && Number(dmy[1]) > 12 && Number(dmy[2]) <= 12) {
    return `${dmy[3]}-${dmy[2].padStart(2, "0")}-${dmy[1].padStart(2, "0")}`;
  }
  const months = {
    jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6,
    jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12,
  };
  const named = s.match(/^(\d{1,2})[\s\-]([A-Za-z]{3,9})\.?[\s\-,]+(\d{4})$/);
  if (named) {
    const m = months[named[2].slice(0, 3).toLowerCase()];
    if (m) return `${named[3]}-${String(m).padStart(2, "0")}-${named[1].padStart(2, "0")}`;
  }
  const namedUs = s.match(/^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$/);
  if (namedUs) {
    const m = months[namedUs[1].slice(0, 3).toLowerCase()];
    if (m) return `${namedUs[3]}-${String(m).padStart(2, "0")}-${namedUs[2].padStart(2, "0")}`;
  }
  return null;
}

/**
 * @param {string} text raw CSV
 * @param {{dedupe?:boolean, normaliseNumbers?:boolean, normaliseDates?:boolean}} opts
 */
function cleanCsv(text, opts = {}) {
  const settings = {
    dedupe: opts.dedupe !== false,
    normaliseNumbers: opts.normaliseNumbers !== false,
    normaliseDates: opts.normaliseDates !== false,
  };
  const raw = parseCsv(text);
  const empty = { inputRows: 0, kept: 0, droppedEmpty: 0, droppedDuplicate: 0, flagged: 0 };
  if (!raw.length) return { headers: [], rows: [], flags: [], stats: empty, csv: "" };

  const headers = raw[0].map((h) => h.replace(/\s+/g, " ").trim());
  const body = raw.slice(1);

  const amountCols = headers
    .map((h, i) => (AMOUNT_HINT.test(h) ? i : -1))
    .filter((i) => i >= 0);
  const dateCols = headers
    .map((h, i) => (DATE_HINT.test(h) && !amountCols.includes(i) ? i : -1))
    .filter((i) => i >= 0);

  const stats = { ...empty, inputRows: body.length };
  const seen = new Set();
  const rows = [];
  const flags = [];

  body.forEach((rawRow, index) => {
    const line = index + 2; // 1-based, +1 for the header row
    const cells = headers.map((_, i) => (rawRow[i] == null ? "" : rawRow[i]).trim());

    if (cells.every((c) => c === "")) {
      stats.droppedEmpty++;
      return;
    }

    if (settings.dedupe) {
      const key = cells.join("\u0001");
      if (seen.has(key)) {
        stats.droppedDuplicate++;
        return;
      }
      seen.add(key);
    }

    if (settings.normaliseNumbers) {
      for (const col of amountCols) {
        const value = cells[col];
        if (!value) continue;
        const num = parseAmount(value);
        if (num == null) {
          flags.push({ line, column: headers[col], value, reason: "not a number — left as typed" });
        } else {
          cells[col] = String(num);
        }
      }
    }

    if (settings.normaliseDates) {
      for (const col of dateCols) {
        const value = cells[col];
        if (!value) continue;
        const day = parseDate(value);
        if (day) cells[col] = day;
        else if (/[0-9]/.test(value)) {
          flags.push({ line, column: headers[col], value, reason: "date is ambiguous — left as typed" });
        }
      }
    }

    rows.push(cells);
  });

  stats.kept = rows.length;
  stats.flagged = flags.length;
  return { headers, rows, flags, stats, csv: toCsv([headers, ...rows]) };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { cleanCsv, parseCsv, toCsv, parseAmount, parseDate };
}
