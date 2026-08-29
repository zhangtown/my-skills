---
name: srt-video-news
description: SRT字幕+音频+素材图片 → Remotion新闻纪录片风格视频。输入SRT文件、MP3音频、佐证素材图片，自动生成带字幕、音频、左文右图布局的可交付MP4视频。依赖 srt-remotion-video 工作流的基础设施。
---

# SRT Video News - 新闻纪录片风格视频生成

将 SRT 字幕 + 音频 + 素材图片转换为新闻纪录片风格的 Remotion 视频。

## 输入要求

用户需要提供：
1. **SRT 字幕文件**（绝对路径）
2. **MP3 音频文件**（绝对路径，与 SRT 时间轴对应）
3. **素材图片**（多个 jpg/png，放在 SRT 同目录下，文件名含描述关键词）

## 工作流概览

```text
┌──────────┐   ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌────────────┐   ┌──────────┐
│ 获取输入 │ → │ 依赖预检 │ → │ 项目初始化 │ → │ 生成分镜 │ → │ 创建场景组件│ → │ 合成视频 │
│ SRT+音频 │   │          │   │ +素材复制  │   │          │   │ 左文右图风格│   │          │
└──────────┘   └──────────┘   └───────────┘   └──────────┘   └────────────┘   └──────────┘
```

## 核心依赖

本 skill 依赖 `srt-remotion-video` skill 的基础设施（分镜生成脚本、项目初始化等）。
两个 skill 默认位于同级目录：

```
~/.agents/skills/
├── srt-remotion-video/     ← 基础设施
└── srt-video-news/         ← 本 skill（新闻风格模板+流程编排）
```

## 视觉风格规范

### 色彩系统

| 用途 | 颜色 | 色值 |
|------|------|------|
| 背景 | 暖米色 | `#F5F2EB` |
| 主文字 | 深黑 | `#1a1a1a` |
| 强调/警示 | 红色 | `#C41E24` |
| 辅助强调 | 深蓝 | `#2E5C8A` |
| 图片说明 | 灰色 | `#888` |

### 布局规范

- **默认布局**：左文右图（flex split，文字占比约45-55%）
- **图片展示**：圆角边框（`borderRadius: 10`）+ 阴影（`boxShadow: 0 10px 34px rgba(0,0,0,.22)`）+ 白色背景
- **图片下方**：灰色图片说明文字（`color: #888`, `fontSize: 18`）
- **标题字体**：`Noto Serif SC`，粗体 900，48-64px
- **正文字体**：`Noto Sans SC` 或系统字体，22-28px
- **字幕位置**：底部居中，白色文字 + 深色阴影 + 半透明黑底

### 组件规范

1. **警示横幅**：`background: linear-gradient(90deg, #C41E24, #8B0000)` + 白色文字
2. **标签**：红色背景 `#C41E24`，白色文字，圆角 6px
3. **流程节点**：白色卡片 + `#d4d0c8` 边框（第三步用红色边框 `#C41E24`）
4. **身份表格**：`borderBottom: 2px dashed #d4d0c8`
5. **对比栏**：`border: 2px solid #C41E24`

## 执行流程

### 步骤 0: 收集输入

1. 确认 SRT 文件绝对路径 `srtPath`
2. 确认 MP3 音频绝对路径 `audioPath`
3. 确认素材图片所在目录（默认与 SRT 同目录）
4. 验证所有文件存在

### 步骤 1: 依赖预检

使用 srt-remotion-video 的模板依赖检查脚本：

```bash
node "{srtRemotionVideoRoot}/scripts/ensure-template-deps.js" "{templateRoot}"
```

其中 `templateRoot` 指向**本 skill 的 template 目录**（不是 srt-remotion-video 的）。

### 步骤 2: 项目初始化

```bash
node "{srtRemotionVideoRoot}/scripts/init-project.js" --srt-path "{srtPath}"
```

获取 `projectRoot`。

### 步骤 3: 复制资源

将音频和素材图片复制到项目 public 目录：

```bash
# 音频
cp "{audioPath}" "{projectRoot}/public/audio.mp3"

# 素材图片（将用户提供的图片复制为 mat01~matNN）
# 按素材文件名中的数字编号，保持映射关系
```

### 步骤 4: 生成分镜

使用 srt-remotion-video 的分镜生成流程：

1. 读取 SRT 内容，按语义分组（参考 `srt-remotion-video` 的 storyboard-parser.md）
2. 生成 `groups.json`，每组控制在 12-18 秒
3. 运行 `generate-storyboard.js` 生成 `storyboard.json`

### 步骤 5: 素材图片映射

**关键步骤**：根据素材文件名中的关键词，映射到对应的分镜场景。

映射示例：
| 素材 | 场景关键词 |
|------|-----------|
| 素材23-适合放在首页-古爱华入职甘肃媒体.jpg | scene_001 开场介绍 |
| 素材1-谁是同胞.jpg | scene_002 调查质疑 |
| 素材21-古爱华照片.jpg | scene_004 身份揭露 |
| 素材4-间谍的时间线.jpg | scene_005 职业履历 |
| 素材7-台独港独疆独.jpg | scene_006/007/008 红线 |

AI 应根据文件名和分镜内容自动判断最佳映射。素材可能有 20+ 个，分到 15 个场景中，个别场景可放 2 张图。

### 步骤 6: 生成场景组件

场景组件**必须**遵循以下模板：

```tsx
import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, Img, staticFile } from "remotion";
const H="#F5F2EB",I="#1a1a1a",R="#C41E24",B="#2E5C8A",r=(f:number,s:number,e:number)=>Math.min(1,Math.max(0,(f-s)/(e-s)));

export const SceneXXX: React.FC<{
  segments: { text: string; relativeStart: number; relativeDuration: number }[];
}> = ({ segments }) => {
  const segCount = segments.length;
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ backgroundColor: H }}>
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 50, width: 1920, height: 1080, padding: "60px 100px" }}>
        <div style={{ flex: "0 1 auto", textAlign: "left", opacity: r(frame, 0, 14) }}>
          {/* 左侧：大标题 + 要点文字，使用 H/I/R/B 颜色常量 */}
        </div>
        <div style={{ flex: "0 1 auto", opacity: r(frame, 8, 22), textAlign: "center" }}>
          <Img src={staticFile("matXX.jpg")} style={{ maxHeight: 550, borderRadius: 10, boxShadow: "0 10px 34px rgba(0,0,0,.22)", background: "#fff" }} />
          <div style={{ color: "#888", fontSize: 18, marginTop: 10 }}>图片说明</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
export default SceneXXX;
```

**关键规则**：
- 颜色常量统一为：`H="#F5F2EB" I="#1a1a1a" R="#C41E24" B="#2E5C8A"`
- 必须引用 `segments`（至少 `segments.length`）以满足校验
- 素材图片用 `staticFile("matXX.ext")` 引用
- 字体用 `"Noto Serif SC", serif` 做大标题

### 步骤 7: 更新 Main.tsx 添加音频和字幕

`Main.tsx` 必须包含：
1. `<Audio src={staticFile("audio.mp3")} />` 音频组件
2. `SubtitleOverlay` 字幕层组件（根据当前帧和 scenes 数据计算显示哪条字幕）

参考 `{templateRoot}/src/compositions/Main.tsx`。

### 步骤 8: 合成与渲染

```bash
cd "{projectRoot}"
node "{srtRemotionVideoRoot}/scripts/generate-scenes-registry.js" "{projectRoot}" "{projectRoot}/storyboard.json"
node "{srtRemotionVideoRoot}/scripts/validate-project.js" "{projectRoot}" "{projectRoot}/storyboard.json"
npx remotion render Main out/output.mp4
```

## 输出

- 输出视频：`{projectRoot}/out/output.mp4`
- 规格：1920×1080, 30fps
- 音频：嵌入视频中
- 字幕：硬编码在视频底部

## 模板文件

### template/src/design-system.ts

```typescript
export const designTokens = {
  background: { host: "#F5F2EB", paper: "#FFFFFF", dark: "#14161c" },
  text: { primary: "#1a1a1a", secondary: "#555", muted: "#888", onDark: "#eee" },
  accent: { primary: "#C41E24", secondary: "#8B0000", blue: "#2E5C8A", gold: "#B8860B" },
  surface: { card: "#FFFFFF", line: "#d4d0c8" },
} as const;
export const hostDecor = {
  gridSize: "0px 0px", gridSizePx: 0, gridOpacity: 0, gridScrollSpeed: 0, sparkles: [] as const,
} as const;
```

### template/src/compositions/Main.tsx

包含 Audio + SubtitleOverlay。详见 template 目录。

## 注意事项

1. 所有路径必须使用绝对路径
2. 素材图片默认从 SRT 同目录读取
3. 场景组件必须引用 `segments` 参数以通过校验
4. 图片说明文字必须简洁（10字以内）
5. 音频文件必须是 MP3 格式
