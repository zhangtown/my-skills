#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建指标数据：读取工作目录 data/*.py 中的指标列表，合并为 data/indicators.json。
用法: python build_indicators.py <工作目录>
约定: 工作目录下 data/dev_part1.py(DEV_1) / data/dev_part2.py(DEV_2) / data/svc.py(SVC)
      （文件名可配置），每份为 dict 列表，字段: num/attr/c1/c2/tender/zong/fen/shot/caption
输出: data/indicators.json {"DEV":[...], "SVC":[...]} 供 build.js 使用。
"""
import sys, os, json, importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    data_dir = os.path.join(base, "data")
    if not os.path.isdir(data_dir):
        sys.exit(f"数据目录不存在: {data_dir}")

    # 收集所有 *dev*.py 与 svc.py（按文件名排序保证顺序稳定）
    dev_files = sorted(f for f in os.listdir(data_dir) if "dev" in f.lower() and f.endswith(".py"))
    svc_files = [f for f in os.listdir(data_dir) if f.lower().startswith("svc") and f.endswith(".py")]

    dev = []
    for f in dev_files:
        mod = load_module("dev_" + f[:-3], os.path.join(data_dir, f))
        for name in dir(mod):
            if name.startswith("DEV") and isinstance(getattr(mod, name), list):
                dev.extend(getattr(mod, name))
    svc = []
    for f in svc_files:
        mod = load_module("svc_" + f[:-3], os.path.join(data_dir, f))
        for name in dir(mod):
            if name.startswith("SVC") and isinstance(getattr(mod, name), list):
                svc.extend(getattr(mod, name))

    if not dev and not svc:
        sys.exit("未找到指标数据（需要 data/dev*.py 与/或 data/svc.py）")

    out = {"DEV": dev, "SVC": svc}
    out_path = os.path.join(data_dir, "indicators.json")
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)

    # 基本完整性校验
    issues = []
    for d in dev + svc:
        for k in ("num", "attr", "c1", "c2", "tender", "zong", "fen"):
            if not d.get(k):
                issues.append((d.get("num"), k))
    attrs = {}
    for d in dev:
        attrs[d["attr"]] = attrs.get(d["attr"], 0) + 1
    print(f"写入 {out_path}")
    print(f"  设备指标: {len(dev)}  服务指标: {len(svc)}")
    print(f"  属性分布: {attrs}")
    if issues:
        print("⚠ 缺字段:", issues[:10])
    # ▲指标截图存在性（shots 目录）
    shots_dir = os.path.join(base, "shots")
    if os.path.isdir(shots_dir):
        missing = [d["num"] for d in dev + svc if d.get("shot") and not os.path.exists(os.path.join(shots_dir, d["shot"]))]
        print("  缺失截图:", missing if missing else "无")

if __name__ == "__main__":
    main()
