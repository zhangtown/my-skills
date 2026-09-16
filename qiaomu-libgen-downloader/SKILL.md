---
name: qiaomu-libgen-downloader
description: 从 LibGen.li 搜索和下载电子书。Use when user wants to download ebooks via LibGen, search for books on LibGen, or mentions "从libgen下载", "libgen下载", "用libgen抓取". Triggers when qiao-epub-bot fails or user explicitly asks for LibGen.
---

# LibGen.li 电子书下载器

通过 LibGen.li 镜像站搜索和下载电子书。无需额外依赖，纯 curl + Python 标准库。

## 快速使用

```bash
# 搜索并下载（自动选第一个可用结果）
python ~/.skills-manager/skills/qiaomu-libgen-downloader/scripts/download.py "书名 作者" -o ~/Downloads/

# 只搜索不下载
python ~/.skills-manager/skills/qiaomu-libgen-downloader/scripts/download.py "书名" --list

# 指定输出目录
python ~/.skills-manager/skills/qiaomu-libgen-downloader/scripts/download.py "Structures J.E. Gordon" -o ~/Books/
```

## 脚本路径

`~/.skills-manager/skills/qiaomu-libgen-downloader/scripts/download.py`（中央技能库；各 Agent 目录下的是指向它的软链接）

## 工作原理

1. 搜索：`https://libgen.li/index.php?req={query}&open=0&res=25&view=simple&phrase=1&column=def`
2. 解析 MD5：`href="/ads.php?md5={md5}"`
3. 获取下载页：`https://libgen.li/ads.php?md5={md5}`
4. 解析下载链接：`href="get.php?md5={md5}&key={key}"`
5. 下载文件，验证 > 10KB
6. 最多重试 3 个 MD5 结果

## 注意事项

- **仅 libgen.li 可用**（libgen.is 被墙）
- 无需 pip 依赖，用系统 Python + curl
- **Windows 上不要写 `python3`**：`%LOCALAPPDATA%\Microsoft\WindowsApps\python3` 是应用商店占位程序，会静默失败；用 `python`
- **路径以中央技能库为准**：不要改成某个 Agent 的目录（`~/.claude`、`~/.dsh`、`~/.pi` 等），否则换 Agent 就失效
- 搜索超时 20s，下载超时 60s
- 文件命名：取书名关键词 + `.epub`
- 批量下载时每次间隔 2 秒避免限频
