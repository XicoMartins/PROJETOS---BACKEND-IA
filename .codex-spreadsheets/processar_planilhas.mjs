import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const projectDir = process.argv[2];
const outputDir = process.argv[3];
const previewDir = path.join(projectDir, ".codex-spreadsheets", "previews-after");
const spreadsheetsDir = path.join(projectDir, "planilhas");
const requiredColumns = ["CLIENTE", "ACABADO", "FERRAMENTAL", "PROCESSO"];

await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

function normalizeHeader(value) {
  return String(value ?? "").trim().toUpperCase();
}

function normalizeId(value) {
  if (value === null || value === undefined || String(value).trim() === "") return null;
  const text = typeof value === "number" && Number.isInteger(value)
    ? String(value)
    : String(value).trim();
  if (!/^\d{1,6}$/.test(text)) throw new Error(`PROCESSO_ID inválido: ${JSON.stringify(value)}`);
  return text.padStart(6, "0");
}

function columnLetter(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

function findProcessSheet(workbook, fileName) {
  for (const worksheet of workbook.worksheets.items) {
    const used = worksheet.getUsedRange(true);
    const values = used?.values ?? [];
    const headers = (values[0] ?? []).map(normalizeHeader);
    if (requiredColumns.every((column) => headers.includes(column))) {
      return { worksheet, values, headers };
    }
  }
  throw new Error(`${fileName}: nenhuma aba contém ${requiredColumns.join(", ")}`);
}

const fileNames = (await fs.readdir(spreadsheetsDir))
  .filter((name) => name.toLowerCase().endsWith(".xlsx") && !name.startsWith("~$"))
  .sort((a, b) => a.localeCompare(b, "pt-BR"));

const entries = [];
const idsInUse = new Map();
let maxId = 0;

for (const fileName of fileNames) {
  const sourcePath = path.join(spreadsheetsDir, fileName);
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
  const sheetInfo = findProcessSheet(workbook, fileName);
  const { values, headers } = sheetInfo;
  const indexes = Object.fromEntries(requiredColumns.map((column) => [column, headers.indexOf(column)]));
  const idIndex = headers.indexOf("PROCESSO_ID");
  const activeRows = [];

  for (let rowIndex = 1; rowIndex < values.length; rowIndex += 1) {
    const row = values[rowIndex] ?? [];
    const present = requiredColumns.filter((column) => String(row[indexes[column]] ?? "").trim() !== "");
    if (present.length === 0) continue;
    if (present.length !== requiredColumns.length) {
      const missing = requiredColumns.filter((column) => !present.includes(column));
      throw new Error(`${fileName}, linha ${rowIndex + 1}: campos obrigatórios vazios: ${missing.join(", ")}`);
    }

    const processId = idIndex >= 0 ? normalizeId(row[idIndex]) : null;
    if (processId) {
      if (idsInUse.has(processId)) {
        throw new Error(
          `PROCESSO_ID duplicado ${processId}: ${idsInUse.get(processId)} e ${fileName}, linha ${rowIndex + 1}`,
        );
      }
      idsInUse.set(processId, `${fileName}, linha ${rowIndex + 1}`);
      maxId = Math.max(maxId, Number(processId));
    }
    activeRows.push({ rowIndex, processId });
  }

  entries.push({ fileName, sourcePath, workbook, ...sheetInfo, idIndex, activeRows });
}

const firstNewId = maxId + 1;
let nextId = firstNewId;
const report = [];

for (const entry of entries) {
  const { fileName, sourcePath, workbook, worksheet, values, idIndex, activeRows } = entry;
  const targetIdIndex = idIndex >= 0 ? idIndex : 6;
  const assigned = [];
  const idsByRow = new Map(activeRows.map(({ rowIndex, processId }) => [rowIndex, processId]));

  for (const activeRow of activeRows) {
    if (!activeRow.processId) {
      if (nextId > 999999) throw new Error("Limite de seis dígitos esgotado");
      const processId = String(nextId).padStart(6, "0");
      nextId += 1;
      if (idsInUse.has(processId)) throw new Error(`PROCESSO_ID já utilizado durante atribuição: ${processId}`);
      idsInUse.set(processId, `${fileName}, linha ${activeRow.rowIndex + 1}`);
      idsByRow.set(activeRow.rowIndex, processId);
      assigned.push(processId);
    }
  }

  const modified = idIndex < 0 || assigned.length > 0;
  const outputPath = path.join(outputDir, fileName);
  if (modified) {
    const lastRowNumber = Math.max(values.length, ...activeRows.map(({ rowIndex }) => rowIndex + 1));
    const sourceColumn = columnLetter(5);
    const targetColumn = columnLetter(targetIdIndex);

    if (idIndex < 0) {
      worksheet
        .getRange(`${targetColumn}1:${targetColumn}${lastRowNumber}`)
        .copyFrom(worksheet.getRange(`${sourceColumn}1:${sourceColumn}${lastRowNumber}`), "all");
    }

    worksheet.getRange(`${targetColumn}1`).values = [["PROCESSO_ID"]];
    const idValues = [];
    for (let rowIndex = 1; rowIndex < lastRowNumber; rowIndex += 1) {
      idValues.push([idsByRow.get(rowIndex) ?? null]);
    }
    if (idValues.length > 0) {
      const idRange = worksheet.getRange(`${targetColumn}2:${targetColumn}${lastRowNumber}`);
      idRange.values = idValues;
      idRange.setNumberFormat("@");
      idRange.format.horizontalAlignment = "center";
    }
    worksheet.getRange(`${targetColumn}1:${targetColumn}${lastRowNumber}`).format.columnWidth = 14;

    const exported = await SpreadsheetFile.exportXlsx(workbook);
    await exported.save(outputPath);
  } else {
    await fs.copyFile(sourcePath, outputPath);
  }

  const preview = await workbook.render({
    sheetName: worksheet.name,
    autoCrop: "all",
    scale: 0.8,
    format: "png",
  });
  const safeName = fileName.replace(/[^A-Za-z0-9.-]+/g, "_").replace(/_+/g, "_");
  await fs.writeFile(
    path.join(previewDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );

  report.push({
    file: fileName,
    sheet: worksheet.name,
    rows: activeRows.length,
    preservedIds: activeRows.length - assigned.length,
    assignedIds: assigned.length,
    firstAssignedId: assigned[0] ?? null,
    lastAssignedId: assigned.at(-1) ?? null,
  });
}

const summary = {
  files: entries.length,
  rows: report.reduce((sum, item) => sum + item.rows, 0),
  preservedIds: report.reduce((sum, item) => sum + item.preservedIds, 0),
  assignedIds: report.reduce((sum, item) => sum + item.assignedIds, 0),
  firstNewId: firstNewId <= nextId - 1 ? String(firstNewId).padStart(6, "0") : null,
  lastId: String(nextId - 1).padStart(6, "0"),
};

await fs.writeFile(
  path.join(outputDir, "relatorio_ids.json"),
  JSON.stringify({ summary, files: report }, null, 2),
  "utf8",
);
console.log(JSON.stringify({ summary, files: report }, null, 2));
