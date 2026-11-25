# 生物信息学手记

[在线阅读](https://loganylchen.github.io/bioinfo-book/) · [下载 EPUB](https://loganylchen.github.io/bioinfo-book/bioinfo-book.epub) · [图版与授权](https://loganylchen.github.io/bioinfo-book/rights.html)

这是独立的 Quarto Book 仓库。`chapters/` 包含入选章节的完整 Markdown（`.qmd`）和正文引用的图片，`_quarto.yml` 是书的目录。使用 Quarto 1.8.27 和 Python 3.10+（`pip install lxml==6.0.2`），运行 `quarto render` 即可在 `_book/` 生成带搜索、上一章／下一章和图版的网页及 EPUB。无需访问原始笔记库。

`publishing/reader.py` 在构建结束时统一排版。文献章从研究问题开始，原归档封面和核验记录移至章末；方法章保留原有的使用条件和顺序。网页使用可折叠的章节目录，EPUB 无需脚本即可阅读全文。旧版样章网址会转到正式章节。

## 更新与选稿

图稿通常放在原笔记旁的 `assets/<笔记名>/`。独立附件目录与已审读的 SVG、Python 示例在 `publishing/attachments.yml` 中逐文件登记；内容变化须重新核对摘要。示例以代码文本进入网页和 EPUB，不在构建时执行。

- 每天香港时间 **07:17**（调度可能延后），从源库 `main` 检查 `References/` 和 `Statistics/`。`Daily/`、`Projects/` 不收。也可在 Actions 手动运行 **Build and publish book**。没有出版变化就不产生提交。
- **文献默认收录，无需 `book_publish: true`。** `References/公众号解读/` 中的文章、`References/` 底下带文献类别、DOI、PMID、论文标题或 citekey 的笔记都能识别；普通 Markdown 也可在开头用 `doi:` 或 DOI 链接。跳过目录、收件箱、附件和模板。「私人研读」「仅供私人学习」及 `archive_scope` 中的私人归档说明不影响文献收录。要连书目也不公开，请设 `book_publish: false`；草稿（`draft: true` 或 `status: draft`）以及 `private: true`、`visibility: private` 仍跳过。
- **分类独立于收录。** 新文献先以题名和已有 DOI 进入「新收文献 · 待归类」。编辑只对新增文献按核心研究问题分篇，在 `publishing/paper-sections.yml` 中登记 DOI（没有则用 citekey 或源相对路径）及 `part`。已有归类不重算，不调用 Copilot 或其他模型；也可以用 `book_part` 给新条目指定篇。新条目的网址不依赖分篇；同 DOI 优先保留首版、其次是专题解读。仅审读过的专题解读登记 `text: true` 后同步全文与图版；个人研读笔记只取书目信息，不拷贝批注、项目链接或附件。
- 首版固定网址在 `publishing/selection.yml`，篇序在 `publishing/sections.yml`。非文献的统计稿仍采用原有选稿或 `book_publish: true` 机制。删除源文后，独有条目随下次同步撤下。公共书仓未配置 PR 触发的私库访问流程。
- 选稿保留 DOI、图注、已记载的授权信息。许可尚未明确的图版标记为**授权待确认**，由书主跟进。`publication_authorized: false` 或注明不得公开转载的文献只收书目信息，不转载正文与图版。常规撤稿不等于清除 Git 历史。
- 改原稿请在源库修改，否则下次同步会覆盖导出版。改主题、排版、目录、选稿规则请在本仓库修改。同步脚本需 Python 3.10+ 和 PyYAML，构建已提交的书稿不需要它们。
