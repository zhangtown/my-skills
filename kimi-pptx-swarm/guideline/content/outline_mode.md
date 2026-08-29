# Outline Mode Workflow

When the user provides a pre-planned outline (per-page content planning, structured outline, hierarchical tree-structured outline, etc.) and requests generating a PPT based on it, enter outline mode.

## workflow

Based on the user requirements and audience analysis completed in generate_slides.md step1, proceed with content design.

### step1. Outline Parsing and Understanding

Identify the type of outline the user has provided:
- **Complete outline**: Page-by-page planning with titles, content points, and page types for each page
- **Semi-structured outline**: Provides chapter divisions and key points, but does not explicitly specify page types or per-page allocation
- **Hierarchical tree outline**: Only provides hierarchical topics and subtopics

Understand the following information from the outline:
- Total page count or content volume
- Content allocation per page/section
- Implicit requirements (e.g., whether cover, table of contents, chapter transition pages are needed)

### step2. Determine User Intent and Complete the Outline

First determine the user's attitude toward content changes, then choose a strategy based on the outline type:

#### User Intent Judgment

- If the user does not explicitly ask you not to modify the content (for example, no content constraint is given, or the user says "enrich this", "there is too little content, add more", "expand the details"): **you must proceed to step3 and supplement text content, arguments, data, cases, and other supporting material**, clearly marking which content was supplemented. However, keep the original outline structure.
- If the user **explicitly asks you not to modify the content** (for example, "follow my outline", "do not add or remove content", "strictly follow the outline"): skip step3 and **strictly follow the user-provided content**. Do not add, delete, expand, or change wording. Only perform necessary pagination and page-type mapping. If cover/final pages are missing, ask the user whether they should be added instead of adding them yourself.

### step3. Information Supplementation (when the user did not explicitly forbid content changes)
- Refer to guideline/search/text_search.md for text supplementation strategies.

### step4. Outline Writing

Based on the user's outline and completion results, use the `write_file` tool to construct the presentation outline `outline.md`.

1. **Faithful to user outline**: The outline structure should align as closely as possible with the user's provided outline content, or reflect the user's content planning, without deviating from the user's intent
2. **Information density**: Plan each page's content reasonably, ensuring natural transitions and substantive, in-depth content on each page.
3. **Page types**: Set a type for each page (cover/table_of_contents/chapter/content/final)
4. **Page count requirements**:
  - When the user's outline already has page count requirements, or content is strictly planned per page: Design according to the user's outline page count
  - When the user's outline does not explicitly require page count, but the outline is highly structured: Page count should match the structured design of the outline
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
- **Content**: Directly retain the original outline wording, or quote the original points from the corresponding section of the outline, and use one sentence to state what this page should present and its intended purpose. If search supplementation was performed, mark it with "[Supplemented]". Do not describe specific chart data, chart types, or other detailed content to be placed. Do not use bullet points. Recommended around 50 words
- **Sources**: Citation numbers or URLs referenced on this page. If prerequisite dependency files contain `[^N^]` citation markers (pointing to URLs in `.citation.jsonl`), annotate the corresponding numbers here; when generating PPTD, these should be converted to `<a href="url">` hyperlinks. If search results are cited, include the source links here, e.g. `https://www.example.com/xxx; ......`

......

## Page x [final]
- **Title**: Title of the ending page
- **Core message**: Core viewpoint/insight/inspiration, or a thought-provoking question, or thank you for watching, etc.
- **Other info**: Information to display on the final page, such as contact details, QR code description, acknowledgment recipients, etc. May be empty
```

## Writing Guidance for PPTD Generation

1. **Make good use of hyperlinks: When the PPT involves reference materials, further reading, or other external resources, use `<a href="url">` to add hyperlinks to related text, making it convenient for the audience to explore further**
2. Faithful to user outline: Strictly build around the user's original points referenced in the outline without deviating from the outline direction
3. Preserve user wording: Key terms, titles, and expressions from the user's outline should retain the original wording as much as possible, without arbitrary rewording
4. Moderate expansion: Transform key points into presentation-ready visual content — neither copying the original text verbatim nor expanding it excessively
5. If the user asks you to strictly follow the outline, organize page content strictly around the user's original points, ensuring every point is presented without adding extra content. Pages with search supplementation should still keep the user's points as the main body, with search-supplemented content integrated as supporting evidence and kept clearly secondary.

## NEXT STEP
1. If visual design is not yet complete, complete it first and generate `design.md`
2. When both `design.md` and `outline.md` are complete, proceed to generate_slides.md step5 to generate the presentation
