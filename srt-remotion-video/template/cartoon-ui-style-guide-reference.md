# New Chinese Style UI Guide Reference

本文件提供 `cartoon-ui-style-guide.css` 的参考信息、示例和速查内容。

## 说明

- `cartoon-ui-style-guide.css` 是**规范主文件**
- 本文档是**参考文档**
- Creator 在规划阶段同时读取主文件与本文件

## 使用建议

### 宿主融合规则

本节是布局与 surface 选择策略的唯一维护入口。主流程和 Creator 协议只负责读取本文件，不重复维护具体视觉偏好。

- 默认宿主背景是浅米杏色 + 极细点阵纹理，因此主体承托面应与宿主背景融合，而不是压出一整块生硬的纯白板
- 不要把纯白或近纯白实体大底板作为唯一主体背景，尤其避免大面积 `cream-card` 直接整块铺开
- 单布局 / 单主体画面优先不要使用明显大边框容器，默认使用无框中央舞台
- 只有小面积信息卡、术语卡、标签页、局部说明可以使用 `cream-card` 或 `paper-section`
- 如果场景主要依赖图解、流程、关系或节点组合，单布局优先使用无框分层承托

### 单布局无框舞台规则

单布局 / 单主体画面指：一个主要图解、一个中心关系图、一个图表、一组围绕中心展开的节点、一个流程主视觉。

规则：

- 单布局默认使用透明根层 + 无框中央舞台，让主体直接生长在宿主浅米杏色点阵背景上
- 单布局不得使用明显大边框容器作为主承托
- 图解、流程、关系、节点组合、图表优先通过图形本身、空间分组、轻阴影、色块、标签、编号和节奏动画建立层级
- `ink-card` / `dark-panel` 是唯一允许作为单布局明显主容器的深色底例外，但仍应作为局部主视觉，不要铺满整屏
- 边框容器可以作为元素级容器，例如小信息卡、术语卡、节点卡、局部标签、对比栏内部卡片、多分区子面板
- 多布局场景（左右对比、三栏并列、多步骤卡片）可以使用卡片子容器，但不要再额外套一个中央大外框

### 颜色使用优先级

- 主要操作 / 强调：`--primary-red`
- 信息 / 中性：`--accent-cream`
- 深色背景：`--primary-ink`
- 印章 / 最高强调：`--primary-seal`
- 背景 / 内容区：`--bg-cream`, `--bg-paper`

### 字体配对建议

- 标题 + 正文：`--font-title` + `--font-body`（经典宋体组合）
- 艺术强调：`--font-accent`（楷体/行书）
- 印章装饰：`--font-seal`（篆刻风）
- 深色背景：使用 `text-cream` 或 `title-hero-light`

### 阴影使用建议

- 卡片 / 容器：`--shadow-sm`
- 深色卡片：`--shadow-dark-md`
- 印章：`--shadow-seal`
- 宣纸内阴影：`--shadow-ink-wash`

## 非规范示例

以下内容仅作为参考模式：

- 列表交错入场
- 墨色卡片场景示例
- 对比卡片示例
- 纹理叠加示例
- 教学场景时序示例

### 示例 1: 列表交错入场

适合功能点、步骤项、要点清单依次出现的场景。

```html
<ul class="rhombus-list stagger-children stagger-md">
  <li class="rhombus-bullet seq-enter-elegant">整合多种格式</li>
  <li class="rhombus-bullet seq-enter-elegant">智能识别内容</li>
  <li class="rhombus-bullet seq-enter-elegant">一键批量转换</li>
</ul>
```

```css
.feature-item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  margin-bottom: var(--space-xs);
  font-family: var(--font-body);
}
```

使用建议：
- 配合 `stagger-sm` 或 `stagger-md`
- 适合信息密度中等的解释场景
- 列表不要太长，3-6 项更合适

### 示例 2: 墨色卡片场景

适合重要说明、数据呈现、结构讲解。

```html
<div class="ink-scene">
  <div class="ink-card">
    <div class="scroll-title">
      <span class="scroll-title-decoration"></span>
      <span class="title-hero-light">核心理念</span>
    </div>
    <ul class="rhombus-list stagger-children">
      <li style="color: var(--text-cream)">典雅 · 克制的视觉语言</li>
      <li style="color: var(--text-cream)">温润 · 书卷气的排版</li>
      <li style="color: var(--text-cream)">沉静 · 高级感的配色</li>
    </ul>
  </div>
</div>
```

```css
.ink-scene {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
}

.ink-list li {
  font-family: var(--font-body);
  font-size: var(--text-large);
  color: var(--text-cream);
  padding: var(--space-xs) 0;
  line-height: var(--line-height-relaxed);
  opacity: 0;
  animation: seq-enter-elegant var(--duration-normal) var(--ease-ink) forwards;
}

.ink-list li::before {
  content: '◇ ';
  color: var(--accent-warm);
  font-size: var(--text-small);
}
```

使用建议：
- 墨色卡片适合作为局部主视觉，不建议整屏铺满
- 文字数量应控制，优先做"要点呈现"而不是大段段落
- 可搭配 `scroll-title-decoration` 红色竖线标题装饰

### 示例 3: 对比卡片布局

适合展示旧方案 / 新方案、错误 / 正确、A / B 对照。

```html
<div class="comparison-container">
  <div class="cream-card comparison-negative">
    <div class="tag-red">旧方案</div>
    <ul class="rhombus-list">...</ul>
  </div>
  <div class="comparison-vs">对</div>
  <div class="cream-card comparison-positive">
    <div class="tag-red">新方案</div>
    <ul class="rhombus-list">...</ul>
  </div>
</div>
```

```css
.comparison-container {
  display: flex;
  align-items: stretch;
  gap: var(--space-xl);
  padding: var(--space-xl);
}

.comparison-negative {
  border-color: var(--text-medium);
  opacity: 0.75;
}

.comparison-positive {
  border-color: var(--primary-red);
  box-shadow: var(--shadow-md);
}

.comparison-vs {
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-title);
  font-size: var(--text-title);
  font-weight: var(--weight-bold);
  color: var(--primary-red);
  writing-mode: vertical-rl;
  letter-spacing: var(--letter-spacing-wide);
}
```

使用建议：
- 推荐配合 `.tag-red` 标签明确标识
- 每侧信息量尽量对齐，避免一侧过重
- 中间对比标识可以使用竖排文字增强国风感

### 示例 4: 纹理叠加

适合给内容区增加纸张氛围，而不改变全局宿主背景。

```html
<div class="textured-scene overlay-xuan">
  <div class="cream-card">
    <h2>宣纸质感内容</h2>
  </div>
</div>
```

```css
.textured-scene {
  width: 100%;
  height: 100%;
  padding: var(--space-xl);
  display: flex;
  align-items: center;
  justify-content: center;
}
```

使用建议：
- `bg-dots` 适合浅米杏色宿主背景上的点阵纸张感
- `overlay-xuan` 适合增加宣纸纹理氛围
- 纹理只做辅助，不要盖过主要信息

### 示例 5: 教学场景时序模板

适合把"标题出现、内容展开、细节补充、强调出现"分阶段实现。

```tsx
const TeachingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const timing = {
    sceneEnter: 0,
    titleEnter: 0.2 * fps,
    contentEnter: 0.4 * fps,
    detailsEnter: 0.6 * fps,
    stagger: 0.08 * fps,
  };

  const titleProgress = spring({
    frame: frame - timing.titleEnter,
    fps,
    config: { damping: 20, stiffness: 120 },
  });

  return (
    <AbsoluteFill style={{ background: 'transparent' }}>
      <div
        style={{
          opacity: titleProgress,
          transform: `translateY(${(1 - titleProgress) * 8}px)`,
        }}
      >
        <h1 className="title-hero">场景标题</h1>
      </div>

      <Sequence from={timing.contentEnter}>
        <ContentArea />
      </Sequence>
    </AbsoluteFill>
  );
};
```

使用建议：
- 标题、主体、细节、强调不要同帧一起出现
- 一个教学场景通常有 3-4 个主要节奏点就够了
- 如果用字幕分段驱动，优先对齐 `segment.relativeStart`
- 使用 `spring` 时 damping 值建议 15-20，保持沉稳感

## 快速参考

### 常用样式变量

- 背景：`--bg-cream`
- 主要文字：`--text-ink`
- 主强调：`--primary-red`
- 标准阴影：`--shadow-sm`
- 标准节奏：`--duration-normal`

### 常用 surface

- `frameless-stage` / `transparent-stage`（单布局默认）
- `cream-card`（局部信息卡）
- `ink-card`（深色重要内容）
- `paper-section`（米色图文区域）
- `seal-stamp` / `seal-badge`（印章标识）
- `scroll-title`（标题装饰）
- `calligraphy-tag`（标签)
- `dark-panel`（深色区块）

### 容器类型速查表

| 容器 | 视觉特征 | 常见用途 |
|------|---------|---------|
| `frameless-stage` / `transparent-stage` | 无明显边框，直接使用宿主背景组织主视觉 | 单布局 / 单主体图解、流程、关系图、图表的默认选择 |
| `cream-card` | 米白半透明纸感卡片，允许宿主底色透出 | 局部信息卡、术语卡、多分区子卡片 |
| `ink-card` | 深墨色背景 + 米白文字 | 重要说明、数据呈现、结构讲解 |
| `paper-section` | 浅米杏色底 + 轻微宣纸纹理 | 图文区域、段落内容、分区背景 |
| `seal-stamp` | 朱红边框方形印章 | 标题标识、概念强调、章节分隔 |
| `seal-badge` | 朱红方印 + 汉字 | 关键词强调、阶段名、标签 |
| `seal-stamp-circle` | 朱红圆形印章 | 数字序号、圆标 |
| `scroll-title` | 红色竖线装饰 + 宋体标题 | 章节标题、场景标题 |
| `rhombus-list` | 菱形项目符号列表 | 要点清单、功能列表、步骤 |
| `dark-panel` | 深墨色面板 + 轻微顶部光晕 | 深色统计、数据总览 |
| `calligraphy-tag` | 细红框 + 楷体标签 | 分类、状态、标注 |
| `circle-number` | 红底白字圆形序号 | 步骤编号、流程序号 |
| `numbered-item` | 圆序号 + 说明文字组合 | 步骤说明、流程介绍 |
| `quote-block` | 左竖线 + 引号装饰 | 引用、经典语录、格言 |

### 大主体容器选择建议

- 图解 / 流程 / 架构说明：单布局优先 `frameless-stage` / `transparent-stage`
- 需要纸面氛围但不想显得廉价：只在小面积信息卡或局部说明中使用 `cream-card` 或 `paper-section`
- 需要深色背景突出：使用 `ink-card` 或 `dark-panel`
- 对比 / 分步：可使用并排 `cream-card`，用红色标签或圆形数字序号区分层级
- 当画面本身已有足够节点、标签、编号、色块和图形关系时，可以直接使用透明根层 + 局部承托，不必额外补一个大底板

### 常用 emphasis

- `tag-red`（红色楷体标签）
- `tag-ink`（墨色标注）
- `rhombus-bullet`（菱形符号）
- `circle-number`（圆形数字序号）
- `seal-stamp-small`（朱红方印）
- `seal-stamp-circle`（朱红圆印）
- `badge`（红底白字标签）
- `scroll-title-decoration`（红色竖线标题装饰）
