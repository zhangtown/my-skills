# plan.json 结构说明 (规划产物 / 全局底稿)

`plan.json` 是 **plan-then-fill** 流水线的核心，在任何正文动笔前一次性冻结所有
"跨章节才能做的决策"。一份三用——

1. **逐叶子生成的依据**：`generate.py` 遍历大纲树，对每个**叶子标题**调 DeepSeek 写正文。
2. **注入每次调用的共享底稿**：`dictionary`(指标/术语/选型)与完整大纲一并塞进每个 prompt。
3. **事后一致性检查的基准**：`check_consistency.py` 拿 `dictionary` 与叶子 `must_keywords` 核对成稿。

`plan.json` 由 `scripts/plan.py` 调 **deepseek-v4-pro** 规划生成（语义抽取）+ Python 确定性
算页数，**冻结前请你审核**。

## 关键概念：叶子标题

**叶子 = 在你给出的大纲里，它底下没有子标题的节点**（按"有没有子标题"判断，不看层数）。
- 一级章节若没下挂任何子标题，它本身就是叶子，整章一次写。
- 三级/四级若是各自分支的最末级，各自是叶子。深度不齐没关系。
- 每个叶子发一次编写调用；非叶子标题只输出标题，内容在其后代叶子里。
- 写叶子时模型可在其内部按需添加**更深一层**的子标题来组织内容（不超过 5 级）。

> **永久规则**：你给出的大纲结构（标题文本、层级、顺序）一律不改、不删、不并、不重排；
> 只能在你已有章节内**细化更深的子标题、填充内容**。

## 顶层结构

```jsonc
{
  "meta": { "project_name": "...", "doc_type": "技术投标文件",
            "bidder": "...", "tender_no": "...", "date": "2026年6月" },

  // —— 篇幅规划（Python 按评分标准确定性算出）——
  "page_plan": {
    "total_pages": 80,             // 你每次调用时给的总页数
    "technical_total_score": 60,   // A：评分标准里技术部分总分
    "pages_per_point": 1.333,      // B = total_pages / A
    "min_pages_per_chapter": 10,   // 一级章节兜底页数（低于则抬到10，再把其余等比缩放保持总页数）
    "words_per_page": 883,         // 每页字数：按正文排版样式查表（见下），word_budget 的乘数
    "body_style": "宋体小四·1.5倍行距"  // 该每页字数对应的正文样式（仅展示）
  },

  // —— 全局数据字典：全篇唯一事实源，注入每次调用，禁止自创/改写 ——
  "dictionary": {
    "metrics": [ {"name":"并发数","value":"≥1000","keywords":["并发"]} ],
    "terms":   [ {"canonical":"一张图","forbidden":["一张图平台"]} ],
    "stack":   [ {"role":"CPU","value":"鲲鹏/飞腾"}, {"role":"数据库","value":"达梦/人大金仓"} ],
    "fixed":   { "项目工期":"10个月" }
  },

  "templates": { "子系统设计": ["功能说明","技术实现","关键指标","架构/流程图"] },

  // —— 大纲树：严格镜像你给的结构。有 children = 非叶子；无 children = 叶子 ——
  "outline": [
    {
      "title": "项目理解与需求分析",     // 一级章节
      "chapter_score": 10,             // 仅一级章节有：映射到本章的技术分数合计
      "chapter_pages": 13.3,           // Python 算出
      "children": [
        { "title": "建设目标",          // 叶子（无 children）
          "brief": "解读采购需求，提出统一数据底座与一张图的总体建设目标。",
          "aspects": [                 // v4-pro 给的"从哪些方面展开"（每条一个撰写角度）
            "当前数据分散、标准不一的现状与痛点",
            "统一数据底座的建设目标与范围",
            "一张图的定位与业务协同价值",
            "目标的可衡量指标与验收标准" ],
          "min_words": 1500,           // v4-pro 给的本节至少字数（内容颗粒度下限参考）
          "scoring_points": ["项目理解"],
          "must_keywords": ["数据底座","一张图","业务协同"],
          "template": null,
          "weight": 2,                 // v4-pro 给的内容轻重，用于章内分页
          "elements": {"table": false, "figure": false},
          "page_budget": 6.7,          // Python：chapter_pages × weight/Σweight
          "word_budget": 4355 }        // Python：round(page_budget × 每页字数)
      ]
    },
    {
      "title": "总体技术方案",
      "chapter_score": 30,
      "children": [
        { "title": "数据接入",          // 非叶子（有 children）→ 只出标题
          "children": [
            { "title": "功能设计", "brief":"...", "weight":1, "must_keywords":["数据接入"],
              "page_budget": 5.0, "word_budget": 3250, "elements":{"figure":true} },
            { "title": "技术实现", "brief":"...", "weight":1, "page_budget":5.0, "word_budget":3250 }
          ]
        }
      ]
    }
  ]
}
```

## 字段说明

`meta` —— 封面信息，透传到 content.json。

`page_plan` —— 篇幅规划（算法见下）。

`dictionary` —— 全局底稿、全篇唯一事实源：`metrics`(标准值+检索词)、`terms`(统一词+禁用同义词)、
`stack`(信创选型)、`fixed`(工期/热线等固定事实)。

`templates` —— 命名的"内部小结构"，叶子用 `template` 按名引用，保同组颗粒度一致。

`outline[]` —— **严格镜像用户大纲的递归树**：
- `title`：标题文本，**不写编号**，引擎自动生成。
- `children`：子节点数组。**有=非叶子，无=叶子**。
- 一级章节(顶层节点)额外有 `chapter_score`、`chapter_pages`。
- 叶子额外有写作字段：`brief`(本节写什么)、`aspects`(从哪些方面/角度逐一展开，3~8 条)、
  `min_words`(本节至少字数，模型给的内容颗粒度下限)、`scoring_points`、`must_keywords`(原样命中)、
  `template`、`weight`(章内分页权重)、`elements`(是否宜出表/图)、`page_budget`、`word_budget`。
  - `aspects` 与 `min_words` 会注入 generate 的每次调用：`aspects` 逐条要求"成段论述、不得一句带过"，
    实际下限取 `max(word_budget, min_words)`。若某叶子在你的大纲里带 `note` 备注（本节写作要求），
    规划阶段会据此细化 `aspects`/`min_words`。

## 篇幅规划算法（Python 确定性）

1. 从评分标准取**技术部分总分 A**（`technical_total_score`）。
2. **每分页数 B = total_pages / A**。
3. 各一级章节技术分 `chapter_score` → 比例页数 `= chapter_score × B`。
4. **兜底**：低于 `min_pages_per_chapter`(默认10) 的一级章节抬到 10 页；其余章节按分数等比缩放，
   使所有一级章节页数之和**仍等于 total_pages**。若总页数连兜底都不够（章节多、总页少），
   兜底自动降为"等分份额的一半"并告警，**仍按分数加权**而非退化等分。
5. **章内分叶**：一级章节页数按各叶子 `weight` 加权分到叶子，`Σ叶子页 = 章节页`；叶子兜底 1 页，
   叶子多于章节页数时兜底同样自动下调并告警。
6. **字数预算** `word_budget = page_budget × words_per_page`，再按 `elements` 扣除版面占用
   （表格 −200 字/个、配图 −220 字/个，下限 250 字），写该叶子时写进 prompt。
   `words_per_page` 由正文排版样式查表（实测值，A4 默认页边距、宋体正文）：

   | 字号 | 固定值22 | 1.5倍行距 | 单倍行距 |
   |------|---------|----------|---------|
   | 四号 | 860 | 731 | 953 |
   | 小四 | 1031 | **883（默认）** | 1299 |

   plan.py 用 `--font-size 四号|小四`、`--line-spacing 固定值22|1.5倍|单倍` 选表，
   或 `--words-per-page N` 直接指定。默认小四+1.5倍=883 字/页。
7. **大叶子拆分**：分页后 `word_budget > --split-threshold`（默认 6000，0=禁用）的叶子，
   plan.py 再调 v4-pro 在该叶子**内部**细化 2~5 个下一级子标题（唯一允许的结构操作），
   父叶变非叶子、子叶成为新叶子。子叶 `weight` 按父叶权重等比缩放（父叶在章内的页数份额
   不变），父叶 `must_keywords` 必须全部分配到子叶（遗漏的自动补到末子叶），然后**重算**
   第 3~6 步。拆分是**迭代**的：子叶若仍超阈值继续拆，最多 3 轮。标题已到第 5 级的叶子
   无法细化，回退 generate.py 的 `--chunk` 分块续写。
