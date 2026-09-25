# Showcase image assets

This directory keeps 32 display PNGs and their 32 editable SVG source files, supplied separately in the local visual proposal and SVG source pack. The images cover four kinds (`hero`, `meta`, `tiktok`, `workflow`) in Chinese and English, light and dark, wide and narrow versions. The PNGs remain the README display assets; SVGs are maintained as editable sources.

Naming: `<kind>.<language>.<theme>.<width>.<format>`, where language is `zh-CN` or `en`, theme is `light` or `dark`, width is `wide` or `narrow`, and format is `png` or `svg`.

The README uses these files with `<picture>`. When changing a graphic, update all relevant versions and keep the accompanying Markdown text, alt text, evidence claims and language pair aligned. See [the style guide](../../showcase-style.md).

[`content.json`](content.json) is the reviewed text contract for these 32 variants and the English/Chinese root READMEs. It keeps the Meta counts/date and TikTok dates/object states in one `facts` block. Language-specific templates define the wording, evidence boundaries and wide/narrow differences. Both themes use the same text contract. This is a consistency source, not independent evidence that the historical claims are true.

Run the standard-library checker after an edit:

```bash
python3 scripts/showcase_content.py
python3 scripts/check_repository.py
python3 -m unittest discover -s tests -p 'test_showcase_content.py' -v
```

The text checker compares every SVG `<text>` entry in order, the two linked case paragraphs and adjacent evidence/date paragraph in each README, all four image alts, and each `<picture>` source's language/theme/width selection. It reports changes to individual values even when the old value still appears elsewhere. Unrelated README numbers, other documentation and the separate social preview are outside this text contract. Whitespace changes are ignored; wording changes require an intentional template update. Missing or invalid manifests fail the check.

For a factual change, review the supporting evidence first, then update `facts`, affected English/Chinese templates, SVG text and README copy together. Keep uncertainty, pending work and preparation/review/delivery/performance distinctions intact. The checker is read-only and does not accept new wording by automatically refreshing the manifest.

The existing PNG and SVG packs were supplied separately. There is no claimed reproducible PNG export pipeline or pixel equivalence between them. Text checks cover SVG/Markdown; the repository check only verifies PNG presence, signature and dimension bounds. After editing a graphic, export and inspect the relevant PNGs manually, including both languages, themes and widths. Also inspect text clipping, layout and accessibility descriptions in the SVGs; text consistency alone does not validate rendering.

`social-preview.svg` and its 1280 × 640 PNG export are separate sharing assets. They are not selected by README `<picture>` and are intended for the repository's GitHub Social preview setting. Keep the PNG below 1 MB and inspect the exported text and safe margins before uploading it.
