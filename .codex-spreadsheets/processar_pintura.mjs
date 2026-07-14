import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = process.argv[2];
const outputPath = process.argv[3];
const previewPath = process.argv[4];

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
const worksheet = workbook.worksheets.getItemAt(0);
const values = worksheet.getUsedRange(true)?.values ?? [];
const headers = (values[0] ?? []).map((value) => String(value ?? "").trim().toUpperCase());
const required = ["CLIENTE", "ACABADO", "FERRAMENTAL", "PROCESSO"];
if (!required.every((column) => headers.includes(column))) {
  throw new Error(`Colunas obrigatórias ausentes: ${required.filter((column) => !headers.includes(column)).join(", ")}`);
}
if (values.length !== 21) throw new Error(`Esperadas 20 linhas de pintura; encontradas ${values.length - 1}`);
if (headers.includes("PROCESSO_ID")) throw new Error("A planilha já possui PROCESSO_ID");

worksheet.getRange("G1:G21").copyFrom(worksheet.getRange("F1:F21"), "all");
worksheet.getRange("G1").values = [["PROCESSO_ID"]];
worksheet.getRange("G2:G21").values = Array.from(
  { length: 20 },
  (_, index) => [String(1123 + index).padStart(6, "0")],
);
worksheet.getRange("G2:G21").setNumberFormat("@");
worksheet.getRange("G2:G21").format.horizontalAlignment = "center";
worksheet.getRange("G1:G21").format.columnWidth = 14;

const inspection = await workbook.inspect({
  kind: "table",
  sheetId: worksheet.name,
  range: "A1:G21",
  include: "values,formulas",
  tableMaxRows: 25,
  tableMaxCols: 8,
  maxChars: 12000,
});
console.log(inspection.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "erros de fórmula",
  maxChars: 2000,
});
console.log(errors.ndjson);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);

const preview = await workbook.render({
  sheetName: worksheet.name,
  range: "A1:G21",
  scale: 1.5,
  format: "png",
});
await fs.mkdir(path.dirname(previewPath), { recursive: true });
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

console.log(JSON.stringify({ outputPath, firstId: "001123", lastId: "001142" }));
