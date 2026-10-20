/**
 * 解析 `docx` 依赖。
 *
 * 审查报告生成器不要求调用方预先 `npm install`：先按常规 ESM 解析，
 * 失败后退回 kimi-docx 技能预置的共享依赖目录
 * （`scripts/setup_node_env ensure-docx` 会把 docx@^9 装到这里）。
 */
import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const candidatePrefixes = () => {
  const prefixes = [];
  for (const key of ["DOCX_NPM_PREFIX", "DOCX_SKILL_NPM_PREFIX"]) {
    if (process.env[key]) prefixes.push(process.env[key]);
  }
  if (process.env.XDG_CACHE_HOME) {
    prefixes.push(path.join(process.env.XDG_CACHE_HOME, "claw-office-docx", "npm"));
  }
  prefixes.push(path.join(os.homedir(), ".cache", "claw-office-docx", "npm"));
  return prefixes;
};

export async function loadDocx() {
  try {
    return await import("docx");
  } catch {
    // 继续走共享依赖目录
  }

  for (const prefix of candidatePrefixes()) {
    const pkgJson = path.join(prefix, "node_modules", "docx", "package.json");
    if (!fs.existsSync(pkgJson)) continue;
    try {
      const require = createRequire(path.join(prefix, "__resolve__.cjs"));
      return require("docx");
    } catch {
      // 换下一个候选目录
    }
  }

  throw new Error(
    [
      "找不到 docx 依赖。任选一种方式安装后重试：",
      "  1) bash <kimi-docx技能目录>/scripts/setup_node_env ensure-docx   （推荐，装到 ~/.cache/claw-office-docx/npm）",
      "  2) 在本目录执行 npm install docx@^9",
      "  3) 设置环境变量 DOCX_NPM_PREFIX 指向已装 docx 的 npm prefix",
    ].join("\n"),
  );
}
