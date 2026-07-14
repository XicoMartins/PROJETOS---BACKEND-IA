import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const backupDir = process.argv[2];
const outputDir = process.argv[3];
const reportPath = process.argv[4];
const required = ["CLIENTE", "ACABADO", "FERRAMENTAL", "PROCESSO"];

function normalize(value) {
  return String(value ?? "").trim();
}

function processSheet(workbook, fileName) {
  for (const worksheet of workbook.worksheets.items) {
    const values = worksheet.getUsedRange(true)?.values ?? [];
    const headers = (values[0] ?? []).map((value) => normalize(value).toUpperCase());
    if (required.every((column) => headers.includes(column))) return { worksheet, values, headers };
  }
  throw new Error(`${fileName}: aba de processos não encontrada`);
}

const files = (await fs.readdir(backupDir))
  .filter((name) => name.toLowerCase().endsWith(".xlsx") && !name.startsWith("~$"))
  .sort((a, b) => a.localeCompare(b, "pt-BR"));
const allIds = new Map();
const results = [];

for (const fileName of files) {
  const before = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(backupDir, fileName)));
  const after = await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(outputDir, fileName)));
  const source = processSheet(before, fileName);
  const result = processSheet(after, fileName);
  const sourceLastRow = source.values.length;
  const resultLastRow = result.values.length;
  const compareRows = Math.max(sourceLastRow, resultLastRow);

  for (let row = 0; row < compareRows; row += 1) {
    for (let col = 0; col < 6; col += 1) {
      const oldValue = source.values[row]?.[col] ?? null;
      const newValue = result.values[row]?.[col] ?? null;
      if (JSON.stringify(oldValue) !== JSON.stringify(newValue)) {
        throw new Error(`${fileName}: valor original alterado em linha ${row + 1}, coluna ${col + 1}`);
      }
    }
  }

  const idIndex = result.headers.indexOf("PROCESSO_ID");
  if (idIndex < 0) throw new Error(`${fileName}: coluna PROCESSO_ID ausente`);
  let processRows = 0;
  for (let row = 1; row < result.values.length; row += 1) {
    const values = result.values[row] ?? [];
    const active = required.every((column) => normalize(values[result.headers.indexOf(column)]) !== "");
    if (!active) continue;
    processRows += 1;
    const processId = normalize(values[idIndex]).padStart(6, "0");
    if (!/^\d{6}$/.test(processId)) throw new Error(`${fileName}, linha ${row + 1}: ID inválido`);
    if (allIds.has(processId)) {
      throw new Error(`ID duplicado ${processId}: ${allIds.get(processId)} e ${fileName}, linha ${row + 1}`);
    }
    allIds.set(processId, `${fileName}, linha ${row + 1}`);
  }

  const errors = await after.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 100 },
    summary: `erros de fórmula em ${fileName}`,
    maxChars: 2000,
  });
  const errorText = errors.ndjson ?? "";
  if (/"matches"\s*:\s*\[[^\]]+\]/s.test(errorText)) {
    throw new Error(`${fileName}: possível erro de fórmula detectado`);
  }

  results.push({ file: fileName, processRows });
}

const numericIds = [...allIds.keys()].map(Number).sort((a, b) => a - b);
for (let expected = 1; expected <= numericIds.length; expected += 1) {
  if (numericIds[expected - 1] !== expected) {
    throw new Error(`Sequência global interrompida antes de ${String(expected).padStart(6, "0")}`);
  }
}

const report = {
  files: results.length,
  processes: allIds.size,
  firstId: String(numericIds[0]).padStart(6, "0"),
  lastId: String(numericIds.at(-1)).padStart(6, "0"),
  duplicates: 0,
  originalValuesChanged: 0,
  formulaErrors: 0,
  details: results,
};
await fs.writeFile(reportPath, JSON.stringify(report, null, 2), "utf8");
console.log(JSON.stringify(report, null, 2));
