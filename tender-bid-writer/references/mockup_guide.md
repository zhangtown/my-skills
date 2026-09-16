# 界面效果图指南 (UI Mockup Guide)

标书涉及功能开发/升级时，为功能类章节生成"像真系统截图"的界面效果图，
插入对应 figure 占位。流水线：**写静态 HTML 界面稿 → Edge 无头截图 PNG → 回填 content.json**。

```bash
# 1. 调 DeepSeek 批量生成界面稿（默认处理图题含"界面"的 figure）：
python scripts/gen_mockups.py content.json plan.json --dir mockups
# 2. 截图 + 回填：
python scripts/render_mockups.py mockups/ --attach content.json
```
界面稿也可以人工写或改（生成不满意时删掉重跑该张，或直接改 html 再截图），
本文其余部分即是写/审界面稿的规范，也是 gen_mockups.py 提示词的依据。

## 命名约定（自动回填的唯一依据）

**HTML 文件名 = figure 块的图题 `title`**（`\ / : * ? " < > |` 替换为 `_`）。
如 content.json 里 `{"type":"figure","title":"样本标注功能界面"}`，
界面稿就叫 `mockups/样本标注功能界面.html`。回填脚本按此匹配，对不上就保持占位框并告警。

## 高保真的关键：像"这个系统"，不是像"某个系统"

1. **业务字段真实**：表格列名、表单项、按钮文字、菜单项一律用本项目的业务词
   （取自 plan.json 的 brief/must_keywords/dictionary），如"图斑编号、变化类型、
   核查状态"，严禁 Lorem/占位文/英文假词。
2. **示例数据可信**：表格填 5~8 行有意义的中文数据（地名、日期、状态各不相同），
   数字符合常识；状态列用彩色标签（待审核/已通过/已驳回）。
3. **界面结构完整**：政企后台标准骨架——顶栏(系统名+用户名) + 左侧菜单(当前项高亮) +
   面包屑 + 内容区(筛选栏/工具栏 + 主体)。地图/图表类页面用 CSS 画示意色块+图例即可。
4. **系统名用真名**：顶栏写招标文件里的系统全称；左侧菜单列大纲里相邻的真实功能模块名，
   让一组截图之间互相印证。

## 视觉规范

- **组件外观走国产政企风**：优先通过 CDN 引入 Element Plus 样式营造熟悉感：
  ```html
  <link rel="stylesheet" href="https://unpkg.com/element-plus/dist/index.css">
  ```
  只借其 CSS 类（`el-button`、`el-table` 风格可手写等效 CSS），**不必引 Vue 跑组件**；
  离线渲染时把 CSS 下载到 mockups/assets/ 本地引用。
- 画布 1440×900（与截图 `--width/--height` 一致），`body{margin:0}`，内容撑满、无滚动条。
- 配色：主色蓝(#1868d3 附近)或招标方行业色，中性灰背景(#f5f7fa)，白色卡片，细边框(#e4e7ed)。
- **避免 AI 味**（沿用 web-artifacts-builder 规范）：不用紫色渐变、不过度居中布局、
  不统一大圆角、不用花哨阴影；后台系统本来就是方正紧凑的。
- 单文件 HTML：样式内联或 `<style>`，不依赖构建工具。

## 与主流水线的衔接

1. 生成阶段（generate.py）模型已按 plan 的 `elements.figure` 输出 figure 占位（有 title 无 img）。
2. 逐个 figure 判断：**功能界面类**（xx功能/xx界面/xx模块）→ 写界面稿；
   架构图/流程图类不适用本流程（另行制图或保留占位框）。
3. `render_mockups.py --attach` 截图并回填后，重跑 build_docx.py，
   图题编号"图x-x"由排版引擎自动维护，任何时候增删图都无需手工改序号。
