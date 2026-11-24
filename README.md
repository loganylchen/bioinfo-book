# 生物信息学手记

[在线阅读](https://loganylchen.github.io/bioinfo-book/) · [下载 EPUB](https://loganylchen.github.io/bioinfo-book/bioinfo-book.epub) · [图版与授权](https://loganylchen.github.io/bioinfo-book/rights.html)

这是独立的 Quarto Book 仓库。`chapters/` 包含入选章节的完整 Markdown（`.qmd`）和正文引用的图片，`_quarto.yml` 是书的目录。使用 Quarto 1.8.27 和 Python 3.10+（`pip install lxml==6.0.2`），运行 `quarto render` 即可在 `_book/` 生成带搜索、上一章／下一章和图版的网页及 EPUB。无需访问原始笔记库。

`publishing/reader.py` 在构建结束时统一排版。文献章从研究问题开始，原归档封面和核验记录移至章末；方法章保留原有的使用条件和顺序。网页使用可折叠的章节目录，EPUB 无需脚本即可阅读全文。旧版样章网址会转到正式章节。

## 更新与选稿

- 每天香港时间 **07:17** 定时检查（GitHub 调度可能延后）。只取 `Statistics/` 和 `References/公众号解读/`；`Daily/`、`Projects/` 和其他目录均不作为内容或附件来源。没有出版变化就不产生提交。可在 Actions 手动运行 **Build and publish book**。
- 首版选稿和固定网址在 `publishing/selection.yml`，主题和篇序在 `publishing/sections.yml`。已有选稿随源文和引用图片更新；删除源文或加 `book_publish: false` 后从当前书站撤下。研究方案会保留原文的待验证说明。
- 新稿公开前，在原 Markdown 的 YAML 头加 `book_publish: true`。可指定 `book_part`（`methods`、`reads`、`atlas`、`genetics`）和 `book_slug`（小写英文和连字符）。统计稿归方法篇；解读稿未指定分篇时按标题和标签归类；不能确定归类或生成稳定网址的，不自动发布。明确标记私人研读、`draft: true` 的稿件不收。公共书仓的发布分支限可信维护者修改，未配置任何 PR 触发的私库访问工作流。
- 选稿保留 DOI、图注、已记载的授权信息。许可尚未明确的图版也收录，状态为**授权待确认**，由书主跟进。明确限制为私人使用的稿件不自动发布。常规撤稿不等于清除 Git 历史。
- 改原稿请在源库修改，否则下次同步会覆盖导出版。改主题、排版、目录、选稿规则请在本仓库修改。同步脚本需 Python 3.10+ 和 PyYAML，构建已提交的书稿不需要它们。
