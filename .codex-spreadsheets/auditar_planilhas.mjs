import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const projectDir = process.argv[2];
const spreadsheetsDir = path.join(projectDir, "planilhas");
const previewDir = path.join(projectDir, ".codex-spreadsheets", "previews-before");
await fs.mkdir(previewDir, { recursive: true });

const names = (await fs.readdir(spreadsheetsDir))
  .filter((name) => name.toLowerCase().endsWith(".xlsx") && !name.startsWith("~$"))
  .sort((a, b) => a.localeCompare(b, "pt-BR"));

const result = [];
for (const name of names) {
  const sourcePath = path.join(spreadsheetsDir, name);
  const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
  const worksheet = workbook.worksheets.getItemAt(0);
  const used = worksheet.getUsedRange(true);
  const values = used?.values ?? [];
  const headers = (values[0] ?? []).map((value) => String(value ?? "").trim());
  const normalized = headers.map((value) => value.toUpperCase());
  const idIndex = normalized.indexOf("PROCESSO_ID");
  const required = ["CLIENTE", "ACABADO", "FERRAMENTAL", "PROCESSO"];
  const missing = required.filter((column) => !normalized.includes(column));
  const dataRows = values.slice(1).filter((row) => row.some((value) => value !== null && value !== ""));
  const ids = idIndex >= 0
    ? dataRows.map((row) => String(row[idIndex] ?? "").trim()).filter(Boolean)
    : [];

  const safeName = name.replace(/[^A-Za-z0-9.-]+/g, "_").replace(/_+/g, "_");
  const preview = await workbook.render({
    sheetName: worksheet.name,
    autoCrop: "all",
    scale: 0.8,
    format: "png",
  });
  await fs.writeFile(
    path.join(previewDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );

  result.push({
    file: name,
    sheet: worksheet.name,
    rows: dataRows.length,
    columns: headers.length,
    headers,
    missing,
    hasProcessId: idIndex >= 0,
    processIds: ids,
  });
}

await fs.writeFile(
  path.join(projectDir, ".codex-spreadsheets", "audit.json"),
  JSON.stringify(result, null, 2),
  "utf8",
);
console.log(JSON.stringify(result, null, 2));
