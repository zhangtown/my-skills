# Search Mode Workflow

When the user provides no outline or long document, only a topic and related requirements, requiring you to search and supplement content on your own, enter search mode.

## workflow

Based on the user requirements and audience analysis completed in generate_slides.md step1, proceed with content design.

### step1. Information Gathering

- Refer to guideline/search/text_search.md for text search strategies

Notes during searching:
- Prioritize data and viewpoints from authoritative sources
- Focus on the latest industry trends and data
- Collect specific case studies as supporting arguments
- Record information sources for subsequent annotation

### step2. Content Reorganization and Narrative Design

Reorganize the gathered information into a narrative structure suitable for presentations:

1. **Narrative logic selection**: Select an appropriate narrative approach based on the topic and audience
   - Industry analysis: Current state -> Trends -> Opportunities and challenges -> Recommendations
   - Knowledge overview: Background -> Core concepts -> Case studies -> Summary
   - Business proposal: Problem -> Analysis -> Solution -> Expected outcomes
   - Or other narrative structures that suit the content characteristics

2. **Content filtering and distillation**
   - Each page should focus on one clear information point, distilling all useful information from the search results
   - Support viewpoints with key data and case studies
   - Ensure accuracy and timeliness of information

### step3. Outline Writing

Based on the content reorganization results, use the `write_file` tool to construct the presentation outline `outline.md`.

1. **Substantive content**: Reference multiple sources, cluster and filter useful information. Each page should have substantive content and data support, prioritizing analytical conclusions, core insights, and key data rather than staying at a surface level
2. **Page transitions**: Content between pages should be interconnected with natural, smooth transitions
3. **Page types**: Set a type for each page (cover/table_of_contents/chapter/content/final)
4. **Page count requirements**:
  - When the user already has page count requirements: Design according to the user's outline page count
  - When the user does not explicitly require page count but provides a structured outline: Page count should match the structured design of the outline
  - No page count requirements or structure: Design based on content volume, recommended 12-18 pages; encouraged to include cover, table of contents, chapters, content, and ending pages
5. Chapter consistency: Either set chapter pages for all chapters or for none -- it is strictly forbidden to have transition pages for some chapters but not others

#### Outline Format

```markdown
# Presentation Outline

## Page 1 [cover]
- **Title**: Title of the presentation
- **Subtitle**: Subtitle of the presentation, may be empty
- **Other info**: Information to display on the cover, such as speaker name, date, organization/company name, logo description, etc. May be empty

## Page 2 [table_of_contents]
- **Title**: Wording such as Table of Contents, Executive Overview, etc.
- **Chapter list**: List all chapter titles in full, which must match the titles of subsequent chapter pages. E.g.:
  1. Chapter One Title
  2. Chapter Two Title
  3. ...

## Page 3 [chapter]
- **Title**: Chapter number and chapter name. E.g.: chapter 1: xxx, 01: xxx, Chapter One: xxx
- **Subtitle**: Chapter subtitle, may be empty
- **Introduction**: Core introduction or overview description of this chapter, helping sub-agents understand the overall direction of the chapter. May be empty

## Page 4 [content]
- **Title**: Title of the page
- **Content**: Distill the core viewpoint from search findings, and use one sentence to summarize the core content this page should convey and its intended purpose. Do not describe specific chart data, chart types, or other detailed content to be placed. Do not use bullet points. Recommended around 50 words
- **Source**: Search information sources referenced for this page (annotated with URL), e.g., https://example.com/report-2025

......

## Page x [final]
- **Title**: Title of the ending page
- **Core message**: Core viewpoint/insight/inspiration, or a thought-provoking question, or thank you for watching, etc.
- **Other info**: Information to display on the final page, such as contact details, QR code description, acknowledgment recipients, etc. May be empty
```

## Writing Guidance for PPTD Generation

1. **Information reliability**: Based on the search sources annotated in the outline, ensure that cited data and viewpoints come from reliable sources. Key data should be attributed on the page (e.g., "According to IDC's 2025 report"), and use `<a href="url">` hyperlinks to point to the original source page, enabling the audience to directly trace and verify
2. **Post-search distillation**: Distill and organize information from search findings before presenting, rather than simply piling up search results
4. **Per-page focus**: Each page should develop around the key points annotated in the outline, supported by data and case studies from the corresponding search findings. Ensure each page has substantive data, case studies, or analysis, rather than staying at a surface-level overview

## NEXT STEP
1. If visual design is not yet complete, complete it first and generate `design.md`
2. When both `design.md` and `outline.md` are complete, proceed to generate_slides.md step5 to generate the presentation
