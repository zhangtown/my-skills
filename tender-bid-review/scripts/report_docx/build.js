#!/usr/bin/env node
/**
 * 投标文件风险审查报告 —— Word 生成器
 *
 * 用法：
 *   node build.js <report.json> <output.docx>
 *
 * 格式规范见 references/report-docx-format.md；
 * 报告 JSON 的块类型见同目录的 example-report.json。
 */
import fs from "node:fs";
import path from "node:path";
import { writeReport } from "./report_style.js";

const [reportPath, outputPath] = process.argv.slice(2);

if (!reportPath || !outputPath) {
  console.error("用法：node build.js <report.json> <output.docx>");
  process.exit(2);
}

if (!fs.existsSync(reportPath)) {
  console.error(`报告 JSON 不存在：${reportPath}`);
  process.exit(1);
}

let report;
try {
  report = JSON.parse(fs.readFileSync(reportPath, "utf8"));
} catch (error) {
  console.error(`报告 JSON 解析失败：${error.message}`);
  process.exit(1);
}

if (!Array.isArray(report.sections) || report.sections.length === 0) {
  console.error("报告 JSON 缺少 sections（正文块数组）");
  process.exit(1);
}

fs.mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });
await writeReport(report, outputPath);
console.log(`written: ${outputPath}`);
