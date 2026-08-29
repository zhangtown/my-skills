# Scene Style Guide - 新闻纪录片风格

本文件定义 `srt-video-news` skill 的场景组件视觉规范。

## 颜色常量

```typescript
const H = "#F5F2EB"; // 背景：暖米色
const I = "#1a1a1a"; // 主文字：深黑
const R = "#C41E24"; // 强调：红色
const B = "#2E5C8A"; // 辅助：深蓝
```

## 布局模板

### 标准布局（左文右图）

```tsx
<AbsoluteFill style={{ backgroundColor: H }}>
  <div style={{
    display: "flex", justifyContent: "center", alignItems: "center",
    gap: 50, width: 1920, height: 1080, padding: "60px 100px"
  }}>
    {/* 左侧：文字区域 */}
    <div style={{ flex: "0 1 auto", textAlign: "left", opacity: r(frame, 0, 14) }}>
      <div style={{ fontFamily: '"Noto Serif SC",serif', fontSize: 56, fontWeight: 900, color: I }}>
        大标题
      </div>
      <div style={{ fontSize: 26, color: "#555", marginTop: 24, lineHeight: 2 }}>
        正文内容...
      </div>
    </div>
    {/* 右侧：佐证图片 */}
    <div style={{ flex: "0 1 auto", opacity: r(frame, 8, 22), textAlign: "center" }}>
      <Img src={staticFile("matXX.jpg")}
        style={{ maxHeight: 550, borderRadius: 10,
          boxShadow: "0 10px 34px rgba(0,0,0,.22)", background: "#fff" }} />
      <div style={{ color: "#888", fontSize: 18, marginTop: 10 }}>图片说明</div>
    </div>
  </div>
</AbsoluteFill>
```

### 双图布局

```tsx
<div style={{ flex: "0 1 auto", display: "flex", gap: 20, opacity: r(frame, 8, 22) }}>
  <Img src={staticFile("matXX.jpg")}
    style={{ maxHeight: 460, borderRadius: 10, boxShadow: "0 10px 34px rgba(0,0,0,.22)", background: "#fff" }} />
  <Img src={staticFile("matYY.jpg")}
    style={{ maxHeight: 460, borderRadius: 10, boxShadow: "0 10px 34px rgba(0,0,0,.22)", background: "#fff" }} />
</div>
```

### 警示横幅

```tsx
<div style={{
  background: "linear-gradient(90deg, #C41E24, #8B0000)",
  color: "#fff", fontFamily: '"Noto Serif SC",serif',
  fontSize: 22, fontWeight: 900, textAlign: "center",
  padding: "20px 30px", borderRadius: 12,
  letterSpacing: ".08em",
  boxShadow: "0 6px 24px rgba(196,30,36,.35)"
}}>
  警示文字
</div>
```

### 标签

```tsx
<span style={{ background: R, color: "#fff", fontWeight: 700,
  padding: "6px 18px", borderRadius: 6, fontSize: 18 }}>
  标签文字
</span>
```

### 流程节点

```tsx
<div style={{
  background: "#fff", border: `2px solid ${isLast ? R : "#d4d0c8"}`,
  borderRadius: 14, padding: "18px 24px",
  textAlign: "center", boxShadow: "0 4px 14px rgba(0,0,0,.06)"
}}>
  <div style={{ fontSize: 22, fontWeight: 700, color: isLast ? R : I }}>步骤名</div>
  <div style={{ fontSize: 16, color: "#666", marginTop: 4 }}>描述</div>
</div>
```

### 身份信息表

```tsx
<table style={{ borderCollapse: "collapse", fontSize: 26 }}>
  <tbody>
    {rows.map(([k, v]) => (
      <tr>
        <td style={{ padding: "12px 20px", borderBottom: "2px dashed #d4d0c8", color: I, fontWeight: 700 }}>{k}</td>
        <td style={{ padding: "12px 20px", borderBottom: "2px dashed #d4d0c8", color: R, fontWeight: 700 }}>{v}</td>
      </tr>
    ))}
  </tbody>
</table>
```

## 动画规范

```typescript
const reveal = (f: number, s: number, e: number) =>
  Math.min(1, Math.max(0, (f - s) / (e - s)));

// 左侧文字：0-14帧淡入
opacity: r(frame, 0, 14)

// 右侧图片：8-22帧淡入（稍晚于文字）
opacity: r(frame, 8, 22)
```

## 校验要求

- 每个场景组件**必须**引用 `segments` 参数（至少 `segments.length`）
- 使用 `export default SceneXXX` 默认导出
- 使用颜色常量 `H/I/R/B` 而非硬编码颜色值
