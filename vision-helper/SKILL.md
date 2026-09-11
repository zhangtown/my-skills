---
name: vision-helper
description: 备用识图通道——仅在当前模型不支持原生图像输入时才需要。先看 ~/.pi/agent/models.json 里当前模型的 input 字段：含 "image"（如 deepseek-flash）就直接用 read 工具读图片，原图进上下文，模型自己能看见，不必用本技能；只有 input 仅含 "text"（如 deepseek-v4-pro）时，才用 node 运行本技能目录下的 vision.js 把图片换成文字描述。
---

# 识图能力（vision-helper）

## 第一步：先判断到底需不需要本技能

1. 取当前模型：`env | grep PI_MODEL`（或 `PI_PROVIDER`）。
2. 查 `~/.pi/agent/models.json` 里该模型条目的 `input` 字段。
3. 判定：

| `input` 内容 | 做法 |
|---|---|
| 含 `"image"`（如 `deepseek-flash`） | **不需要本技能**。直接 `read` 图片文件的绝对路径，或让用户把图贴进对话/复制到剪贴板（可用 PowerShell `[Windows.Forms.Clipboard]::GetImage()` 落盘），图片作为附件原图进入上下文，模型自己就能识别。 |
| 只有 `"text"`（如 `deepseek-v4-pro`） | 用下面的 `vision.js` 把图片转成文字描述后再使用。 |

PiDeck 视觉日志（`~/.pi/agent/pi-deck-vision.log`）会给出佐证：

- `tool_result: 1 image(s) bypassed: current model declares image input support` → 原图直通模型，无需转换
- `tool_result: converted 1 image(s)` → 走了转换通道（说明当时模型是纯文本的）

## 使用方式（仅在纯文本模型下）

脚本位置：本 SKILL.md 所在目录下的 `vision.js`（以下用 `<skill_dir>` 表示该目录）。

本地图片：

```shell
node "<skill_dir>/vision.js" "图片的绝对路径" "请用中文详细描述这张图片的内容"
```

网络图片：

```shell
node "<skill_dir>/vision.js" --url "https://example.com/image.jpg" "请用中文详细描述这张图片的内容"
```

## 配置信息

默认复用 pi 自己的模型配置，**不需要第三方账户余额**：

- 读取 `~/.pi/agent/models.json` → `providers.deepseek`，用它的 `baseUrl` + `apiKey`，
  并优先挑选声明了 `image` 输入的模型（当前为 `deepseek-flash`）。
- 覆盖优先级：环境变量 > models.json(deepseek) > 内嵌常量（MWY `gpt-5.6`，**该账户已欠费，
  调用会返回 403 INSUFFICIENT_BALANCE，不要依赖**）。
- 可覆盖的环境变量：`VISION_BASE_URL`、`VISION_API_KEY`、`VISION_MODEL`（兼容旧变量
  `DASHSCOPE_BASE_URL`、`DASHSCOPE_API_KEY`）。

## 触发场景

- 当前模型只声明 text 输入，而上游给了图片
- 用户明确要求"用识图技能看一下"（而不是直接把图给模型）
