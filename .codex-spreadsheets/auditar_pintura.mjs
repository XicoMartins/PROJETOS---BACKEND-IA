import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const sourcePath = process.argv[2];
const outputDir = process.argv[3];
await fs.mkdir(outputDir, { recursive: true });

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(sourcePath));
const worksheet = workbook.worksheets.getItemAt(0);
const used = worksheet.getUsedRange(true);
const values = used?.values ?? [];

const inspection = await workbook.inspect({
  kind: "table,computedStyle",
  sheetId: worksheet.name,
  range: `A1:G${Math.max(values.length, 25)}`,
  include: "values,formulas",
  tableMaxRows: 30,
  tableMaxCols: 8,
  maxChars: 12000,
});
await fs.writeFile(path.join(outputDir, "pintura-inspect.ndjson"), inspection.ndjson, "utf8");

const preview = await workbook.render({
  sheetName: worksheet.name,
  autoCrop: "all",
  scale: 1.5,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, "pintura-before.png"),
  new Uint8Array(await preview.arrayBuffer()),
);

console.log(JSON.stringify({ sheet: worksheet.name, rows: values.length, values }, null, 2));
