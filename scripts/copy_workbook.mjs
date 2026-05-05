import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [, , command, inputPath, outputPath] = process.argv;

if (!command || !inputPath || !outputPath) {
  throw new Error("Usage: node scripts/copy_workbook.mjs <export|import> <input> <output>");
}

if (command === "export") {
  const rows = JSON.parse(await fs.readFile(inputPath, "utf8"));
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add("Copy");
  const matrix = [
    ["page_or_area", "field_key", "current_text", "notes"],
    ...rows.map((row) => [row.page_or_area, row.field_key, row.current_text, row.notes]),
  ];

  const range = sheet.getRange(`A1:D${matrix.length}`);
  range.values = matrix;

  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  process.exit(0);
}

if (command === "import") {
  const input = await FileBlob.load(inputPath);
  const workbook = await SpreadsheetFile.importXlsx(input);
  const inspected = await workbook.inspect({
    kind: "table",
    range: "Copy!A1:D500",
    include: "values",
    tableMaxRows: 500,
    tableMaxCols: 4,
  });

  const lines = inspected.ndjson
    .trim()
    .split("\n")
    .map((line) => JSON.parse(line))
    .filter((row) => Array.isArray(row?.values));

  const tableRows = lines.at(-1)?.values ?? [];
  const dataRows = tableRows.slice(1).filter((row) => row[1]);
  const rows = dataRows.map((row) => ({
    page_or_area: String(row[0] ?? ""),
    field_key: String(row[1] ?? ""),
    current_text: String(row[2] ?? ""),
    notes: String(row[3] ?? ""),
  }));

  await fs.writeFile(outputPath, `${JSON.stringify(rows, null, 2)}\n`, "utf8");
  process.exit(0);
}

throw new Error(`Unknown command: ${command}`);
