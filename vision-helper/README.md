# vision-helper 识图技能

让没有原生识图能力的模型也能“看图”：把图片转成 base64，发给支持视觉的 OpenAI 兼容接口（当前配置为 `gpt-5.6` @ `https://open.mwy.asia/v1`），再把文字描述返回。

## 文件说明

- `vision.js`：核心脚本，配置已内嵌，也支持环境变量覆盖
- `SKILL.md`：Codex 技能说明，告诉 AI 何时以及如何调用

## 手动调用

```shell
node vision.js "图片的绝对路径" "请用中文详细描述这张图片的内容"
node vision.js --url "https://example.com/image.jpg" "请用中文详细描述这张图片的内容"
```

## 覆盖配置（可选）

设置环境变量 `VISION_BASE_URL`、`VISION_API_KEY`、`VISION_MODEL` 即可覆盖默认值，无需改代码。
