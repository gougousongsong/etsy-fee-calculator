const assert = require("node:assert");
const { cleanCsv, parseAmount, parseDate } = require("./cleaner.js");

let pass = 0;
function ok(name, fn) {
  try {
    fn();
    pass++;
    console.log("  ✓", name);
  } catch (e) {
    console.error("  ✗", name, "\n   ", e.message);
    process.exitCode = 1;
  }
}

console.log("amounts");
ok('"$1,234.50" -> 1234.5', () => assert.equal(parseAmount("$1,234.50"), 1234.5));
ok('"1.234,50" -> 1234.5', () => assert.equal(parseAmount("1.234,50"), 1234.5));
ok('"(45.00)" -> -45', () => assert.equal(parseAmount("(45.00)"), -45));
ok('"1 200,00 €" -> 1200 (space thousands, decimal comma)', () =>
  assert.equal(parseAmount("1 200,00 €"), 1200));
ok('"1,200" -> 1200 (thousands comma)', () => assert.equal(parseAmount("1,200"), 1200));
ok('"1200,00" -> 1200 (decimal comma, not 120000)', () => assert.equal(parseAmount("1200,00"), 1200));
ok('"1,2,3" -> null (ambiguous, never guessed)', () => assert.equal(parseAmount("1,2,3"), null));
ok('"abc" -> null', () => assert.equal(parseAmount("abc"), null));

console.log("dates");
ok('"2026-03-04" stays', () => assert.equal(parseDate("2026-03-04"), "2026-03-04"));
ok('"04/03/2026" (US order, month first) -> 2026-04-03', () =>
  assert.equal(parseDate("04/03/2026"), "2026-04-03"));
ok('"25/12/2025" (day > 12) -> 2025-12-25', () => assert.equal(parseDate("25/12/2025"), "2025-12-25"));
ok('"12 Mar 2025" -> 2025-03-12', () => assert.equal(parseDate("12 Mar 2025"), "2025-03-12"));

console.log("cleaning a messy sheet");
const messy = [
  "order id , customer , amount , order_date ",
  '1, Alice ,"$1,200.00", 04/03/2026 ',
  "2,Bob,45.00,2026-03-05",
  ",,,", // entirely empty
  '1, Alice ,"$1,200.00", 04/03/2026 ', // exact duplicate
  "3,Carol,not-a-number,13/13/2026", // flagged twice, row kept
  '4,"Dave, Jr.",99.5,5 Mar 2026',
].join("\n");

const result = cleanCsv(messy);
ok("header trimmed", () => assert.deepEqual(result.headers, ["order id", "customer", "amount", "order_date"]));
ok("empty row dropped", () => assert.equal(result.stats.droppedEmpty, 1));
ok("duplicate dropped", () => assert.equal(result.stats.droppedDuplicate, 1));
ok("4 real rows kept", () => assert.equal(result.stats.kept, 4));
ok("amounts normalised", () =>
  assert.deepEqual(result.rows.map((r) => r[2]), ["1200", "45", "not-a-number", "99.5"]));
ok("dates normalised", () =>
  assert.deepEqual(result.rows.map((r) => r[3]), ["2026-04-03", "2026-03-05", "13/13/2026", "2026-03-05"]));
ok("bad amount flagged", () =>
  assert.ok(result.flags.some((f) => f.column === "amount" && f.value === "not-a-number")));
ok("bad date flagged", () =>
  assert.ok(result.flags.some((f) => f.column === "order_date" && f.value === "13/13/2026")));
ok("quoted comma survives", () => assert.equal(result.rows[3][1], "Dave, Jr."));
ok("no cell is silently emptied", () =>
  assert.ok(result.rows.every((r) => r.every((c) => c !== undefined && c !== null))));

console.log("round trip");
ok("output re-parses to the same number of rows", () => {
  const again = cleanCsv(result.csv);
  assert.equal(again.stats.kept, result.rows.length);
  assert.equal(again.flags.length, result.flags.length);
});

console.log("money must not be lost");
ok("sum of amounts unchanged by cleaning", () => {
  const sum = result.rows
    .filter((r) => /^-?\d+(\.\d+)?$/.test(r[2]))
    .reduce((a, r) => a + Number(r[2]), 0);
  assert.equal(Math.round(sum * 100) / 100, 1344.5);
});

console.log(`\n${pass} passed`);
