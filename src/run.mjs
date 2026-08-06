import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { classifyPdf, extractTextInRegions } from "@firecrawl/pdf-inspector";
import { PDFDocument } from "pdf-lib";
import xlsx from "xlsx";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const workspaceRoot = path.resolve(projectRoot, "..");

const defaults = {
  workbook: path.join(workspaceRoot, "UP_1971_Amenities_Page_Plan_With_Totals.xlsx"),
  pdfRoot: path.join(
    workspaceRoot,
    "1971-20260725T134344Z-1-001",
    "1971",
    "Uttar Pradesh",
  ),
  outputRoot: path.join(projectRoot, "output"),
};

const CATEGORY_DIRS = {
  civic: "Civic Amenities",
  mededu: "Medical_Education",
  tehsil: "Tehsil_Appendix",
  villages: "Villages",
};

function parseArgs(argv) {
  const args = {
    workbook: defaults.workbook,
    pdfRoot: defaults.pdfRoot,
    outputRoot: defaults.outputRoot,
    district: null,
    sheet: null,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const current = argv[i];
    const next = argv[i + 1];
    if (current === "--") {
      continue;
    } else if (current === "--workbook" && next) {
      args.workbook = path.resolve(next);
      i += 1;
    } else if (current === "--pdf-root" && next) {
      args.pdfRoot = path.resolve(next);
      i += 1;
    } else if (current === "--output" && next) {
      args.outputRoot = path.resolve(next);
      i += 1;
    } else if (current === "--district" && next) {
      args.district = normalizeDistrict(next);
      i += 1;
    } else if (current === "--sheet" && next) {
      args.sheet = next;
      i += 1;
    } else if (current === "--help") {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown or incomplete argument: ${current}`);
    }
  }

  return args;
}

function printHelp() {
  console.log(`Usage: pnpm trim -- [options]

Options:
  --workbook <path>   Workbook path
  --pdf-root <path>   Root folder containing Uttar Pradesh 1971 PDFs
  --output <path>     Output folder
  --district <name>   Only process one district
  --sheet <name>      One of: Tehsil_and_Town, Village_Level
  --help              Show help
`);
}

function normalizeDistrict(value) {
  return String(value).trim().toLowerCase().replace(/\s+/g, " ");
}

function slugify(value) {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function parseRange(value) {
  if (value == null || value === "") {
    return null;
  }

  if (typeof value === "number") {
    return { start: value, end: value };
  }

  const text = String(value).trim();
  const rangeMatch = text.match(/^(\d+)\s*-\s*(\d+)$/);
  if (rangeMatch) {
    return { start: Number(rangeMatch[1]), end: Number(rangeMatch[2]) };
  }

  const singleMatch = text.match(/^(\d+)$/);
  if (singleMatch) {
    return { start: Number(singleMatch[1]), end: Number(singleMatch[1]) };
  }

  return null;
}

function expandRanges(ranges) {
  const pages = [];
  for (const range of ranges) {
    for (let page = range.start; page <= range.end; page += 1) {
      pages.push(page);
    }
  }
  return pages;
}

function buildPlan(workbookPath) {
  const workbook = xlsx.readFile(workbookPath, { cellDates: false });
  const tehsilTownRows = xlsx.utils.sheet_to_json(workbook.Sheets.Tehsil_and_Town, {
    defval: null,
  });
  const villageRows = xlsx.utils.sheet_to_json(workbook.Sheets.Village_Level, {
    defval: null,
  });

  const plan = new Map();

  for (const row of tehsilTownRows) {
    const district = row.District;
    const sourcePdf = row["Source PDF"];
    if (!district || !sourcePdf) {
      continue;
    }

    const key = normalizeDistrict(district);
    const spec = plan.get(key) ?? {
      district,
      sourcePdf,
      town: {},
      villages: [],
      notes: [],
    };

    spec.town.civic = parseRange(row["Town Statement IV: Civic amenities pages"]);
    spec.town.mededu = parseRange(row["Town Statement V: Medical/Education pages"]);
    spec.town.tehsil = parseRange(row["Tahsil appendix pages"]);
    if (row["Verification note"]) {
      spec.notes.push(String(row["Verification note"]).trim());
    }
    plan.set(key, spec);
  }

  for (const row of villageRows) {
    if (!row.District || !row["Source PDF"]) {
      continue;
    }

    if (String(row.Tahsil).trim().toUpperCase() === "DISTRICT TOTAL") {
      continue;
    }

    const key = normalizeDistrict(row.District);
    const spec = plan.get(key) ?? {
      district: row.District,
      sourcePdf: row["Source PDF"],
      town: {},
      villages: [],
      notes: [],
    };

    spec.villages.push({
      tahsil: row.Tahsil,
      range: {
        start: Number(row["Printed page start"]),
        end: Number(row["Printed page end"]),
      },
    });

    if (row["Verification note"]) {
      spec.notes.push(String(row["Verification note"]).trim());
    }

    plan.set(key, spec);
  }

  return plan;
}

function getPageBoxes(pdfDoc) {
  return pdfDoc.getPages().map((page) => {
    const { width, height } = page.getSize();
    return [0, 0, width, height];
  });
}

async function extractPageTexts(pdfBytes, pageBoxes, pageIndexes) {
  const chunks = [];
  const orderedIndexes = [...new Set(pageIndexes)].sort((a, b) => a - b);
  const chunkSize = 16;

  for (let start = 0; start < orderedIndexes.length; start += chunkSize) {
    const slice = orderedIndexes.slice(start, start + chunkSize);
    const pageRegions = slice.map((pageIndex) => ({
      page: pageIndex,
      regions: [pageBoxes[pageIndex]],
    }));
    const extracted = extractTextInRegions(pdfBytes, pageRegions);
    chunks.push(...extracted);
  }

  const byPage = new Map();
  for (const item of chunks) {
    const region = item.regions[0] ?? { text: "", needsOcr: true };
    byPage.set(item.page, region);
  }
  return byPage;
}

function normalizeText(text) {
  return String(text ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function getLeadingPageNumber(text) {
  const snippet = String(text ?? "").slice(0, 80).replace(/\s+/g, " ").trim();
  const match = snippet.match(/^(\d{1,4})\b/);
  return match ? Number(match[1]) : null;
}

function findMarker(pageTexts, pageIndexes, matcher) {
  for (const pageIndex of pageIndexes) {
    const region = pageTexts.get(pageIndex);
    if (!region || !region.text) {
      continue;
    }

    const text = normalizeText(region.text);
    if (!matcher(text)) {
      continue;
    }

    const printed = getLeadingPageNumber(region.text);
    if (printed == null) {
      continue;
    }

    return {
      actualPage: pageIndex + 1,
      printedPage: printed,
      needsOcr: Boolean(region.needsOcr),
      preview: region.text.slice(0, 160).replace(/\s+/g, " ").trim(),
    };
  }

  return null;
}

function resolveRange(range, offset) {
  return {
    start: range.start + offset,
    end: range.end + offset,
  };
}

function validateResolvedRange(range, pageCount) {
  return range.start >= 1 && range.end >= range.start && range.end <= pageCount;
}

function dedupe(values) {
  return [...new Set(values)];
}

async function ensureDir(dirPath) {
  await fs.mkdir(dirPath, { recursive: true });
}

async function writeSubsetPdf(sourceDoc, ranges, outputPath) {
  const outDoc = await PDFDocument.create();
  for (const range of ranges) {
    const indexes = [];
    for (let page = range.start; page <= range.end; page += 1) {
      indexes.push(page - 1);
    }
    const copiedPages = await outDoc.copyPages(sourceDoc, indexes);
    for (const page of copiedPages) {
      outDoc.addPage(page);
    }
  }
  const bytes = await outDoc.save();
  await fs.writeFile(outputPath, bytes);
}

function categoryFilename(district, category) {
  const slug = slugify(district);
  if (category === "civic") {
    return `${slug}_civic_1971.pdf`;
  }
  if (category === "mededu") {
    return `${slug}_mededu_1971.pdf`;
  }
  if (category === "tehsil") {
    return `${slug}_tehsil_1971.pdf`;
  }
  return `${slug}_villages_1971.pdf`;
}

async function processDistrict(spec, options) {
  const sourcePath = path.join(options.pdfRoot, spec.sourcePdf);
  const pdfBytes = await fs.readFile(sourcePath);
  const sourceDoc = await PDFDocument.load(pdfBytes);
  const pageCount = sourceDoc.getPageCount();
  const pageBoxes = getPageBoxes(sourceDoc);
  const classification = classifyPdf(Buffer.from(pdfBytes));

  const earlyPages = Array.from({ length: Math.min(pageCount, 90) }, (_, index) => index);
  const lateStart = Math.max(0, pageCount - 40);
  const latePages = Array.from({ length: pageCount - lateStart }, (_, index) => lateStart + index);
  const pageTexts = await extractPageTexts(pdfBytes, pageBoxes, [...earlyPages, ...latePages]);

  const townMarker = findMarker(pageTexts, earlyPages, (text) => {
    return text.includes("town statement") && text.includes("civic and other");
  });
  const medMarker = findMarker(pageTexts, earlyPages, (text) => {
    return text.includes("town statement") && text.includes("medical");
  });
  const villageMarker = findMarker(pageTexts, earlyPages, (text) => {
    return text.includes("village") && text.includes("amenities and");
  });
  const appendixMarker = findMarker(pageTexts, latePages, (text) => {
    return text.includes("appendix") && text.includes("tahsil") && text.includes("abstract");
  });

  const report = {
    district: spec.district,
    sourcePdf: spec.sourcePdf,
    sourcePath,
    pageCount,
    pdfType: classification.pdfType,
    confidence: classification.confidence,
    pagesNeedingOcr: classification.pagesNeedingOcr.map((page) => page + 1),
    notes: dedupe(spec.notes),
    markers: {
      townMarker,
      medMarker,
      villageMarker,
      appendixMarker,
    },
    outputs: {},
    warnings: [],
  };

  const townOffset = townMarker
    ? townMarker.actualPage - townMarker.printedPage
    : medMarker
      ? medMarker.actualPage - medMarker.printedPage
      : null;
  const villageOffset = villageMarker ? villageMarker.actualPage - villageMarker.printedPage : null;
  const appendixOffset = appendixMarker
    ? appendixMarker.actualPage - appendixMarker.printedPage
    : villageOffset ?? townOffset;

  if (townOffset == null && options.sheet !== "Village_Level") {
    report.warnings.push("Could not infer town-section offset.");
  }
  if (villageOffset == null && options.sheet !== "Tehsil_and_Town") {
    report.warnings.push("Could not infer village-section offset.");
  }
  if (!appendixMarker) {
    report.warnings.push("Could not find appendix marker; using fallback offset.");
  }

  const targets = [];
  if (options.sheet == null || options.sheet === "Tehsil_and_Town") {
    if (spec.town.civic && townOffset != null) {
      targets.push({ category: "civic", ranges: [resolveRange(spec.town.civic, townOffset)] });
    }
    if (spec.town.mededu && townOffset != null) {
      targets.push({ category: "mededu", ranges: [resolveRange(spec.town.mededu, townOffset)] });
    }
    if (spec.town.tehsil && appendixOffset != null) {
      targets.push({ category: "tehsil", ranges: [resolveRange(spec.town.tehsil, appendixOffset)] });
    }
  }

  if ((options.sheet == null || options.sheet === "Village_Level") && spec.villages.length > 0 && villageOffset != null) {
    targets.push({
      category: "villages",
      ranges: spec.villages.map((item) => resolveRange(item.range, villageOffset)),
      tahsils: spec.villages.map((item) => ({
        tahsil: item.tahsil,
        printedRange: item.range,
        actualRange: resolveRange(item.range, villageOffset),
      })),
    });
  }

  for (const target of targets) {
    const invalidRanges = target.ranges.filter((range) => !validateResolvedRange(range, pageCount));
    if (invalidRanges.length > 0) {
      report.outputs[target.category] = {
        status: "skipped",
        reason: "resolved ranges fall outside the PDF page count",
        resolvedRanges: target.ranges,
      };
      report.warnings.push(
        `${target.category}: resolved page range is out of bounds for ${spec.district}.`,
      );
      continue;
    }

    const categoryDir = path.join(options.outputRoot, CATEGORY_DIRS[target.category]);
    await ensureDir(categoryDir);
    const outputPath = path.join(categoryDir, categoryFilename(spec.district, target.category));
    await writeSubsetPdf(sourceDoc, target.ranges, outputPath);

    const actualPages = expandRanges(target.ranges);
    const ocrPages = actualPages.filter((page) => classification.pagesNeedingOcr.includes(page - 1));
    report.outputs[target.category] = {
      status: "written",
      outputPath,
      resolvedRanges: target.ranges,
      ocrRiskPages: ocrPages,
    };

    if (ocrPages.length > 0) {
      report.warnings.push(
        `${target.category}: pages ${ocrPages.join(", ")} may need OCR for reliable text extraction.`,
      );
    }

    if (target.tahsils) {
      report.outputs[target.category].tahsils = target.tahsils;
    }
  }

  return report;
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  await ensureDir(options.outputRoot);
  await ensureDir(path.join(options.outputRoot, "reports"));

  const plan = buildPlan(options.workbook);
  const districts = [...plan.values()].filter((spec) => {
    if (!options.district) {
      return true;
    }
    return normalizeDistrict(spec.district) === options.district;
  });

  if (districts.length === 0) {
    throw new Error("No districts matched the current filters.");
  }

  const reports = [];
  for (const spec of districts) {
    console.log(`Processing ${spec.district}...`);
    const report = await processDistrict(spec, options);
    reports.push(report);
  }

  const reportPath = path.join(options.outputRoot, "reports", "trim-report.json");
  await fs.writeFile(reportPath, `${JSON.stringify(reports, null, 2)}\n`, "utf8");

  const summary = reports.map((report) => {
    return {
      district: report.district,
      pdfType: report.pdfType,
      warnings: report.warnings.length,
      written: Object.values(report.outputs).filter((output) => output.status === "written").length,
      skipped: Object.values(report.outputs).filter((output) => output.status !== "written").length,
    };
  });

  console.table(summary);
  console.log(`Report: ${reportPath}`);
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
