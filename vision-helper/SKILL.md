---
name: vision-helper
description: 识别图片内容（本地图片或网络图片 URL）。当用户分享图片、图片路径、图片链接或附件，或要求分析、描述、识别图片内容时，用 node 运行本技能目录下的 vision.js，把图片发送给视觉模型（gpt-5.6），用返回的文字描述代替原生识图。Use when the user shares an image or asks to analyze, describe, or recognize an image and the model needs vision capability.
---

# 识图能力（vision-helper）

你的底层模型不具备原生识图能力时，遇到图片不要依赖 Read/查看工具直接读取图片内容，改用本技能目录下的 `vision.js` 调用视觉模型，把图片转成文字描述后再使用。

## 使用方式

脚本位置：本 SKILL.md 所在目录下的 `vision.js`（以下用 `<skill_dir>` 表示该目录）。

本地图片：

```shell
node "<skill_dir>/vision.js" "图片的绝对路径" "请用中文详细描述这张图片的内容"
```

网络图片：

```shell
node "<skill_dir>/vision.js" --url "https://example.com/image.jpg" "请用中文详细描述这张图片的内容"
```

## 触发场景

- 用户分享图片路径（本地或网络 URL）
- 消息中出现图片附件
- 用户要求分析、描述、识别图片内容

## 配置信息

- 视觉模型：`gpt-5.6`（已实测支持识图；`gpt-5.6-luna` 在当前账号未开通计费，开通后可通过环境变量 `VISION_MODEL` 切回）
- API Base URL：`https://open.mwy.asia/v1`
- API Key 已内嵌在 `vision.js` 中
- 可用环境变量覆盖：`VISION_BASE_URL`、`VISION_API_KEY`、`VISION_MODEL`（兼容旧变量 `DASHSCOPE_BASE_URL`、`DASHSCOPE_API_KEY`）

处理多张图片时，逐张执行脚本，拿齐所有描述后再回复用户。
