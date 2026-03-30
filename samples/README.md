# Sample Fixtures

These tiny CSVs are deterministic fixtures for `embedumap` development and smoke tests.

## Files

- `blog-text.csv`: text-focused rows derived from `/home/sanand/code/blog/analysis/embeddings/documents.csv`
- `blog-text-300.csv`: a ~300-row text-only smoke test slice derived from `/home/sanand/code/blog/analysis/embeddings/documents.csv`
- `calvin-images.csv`: image-focused rows derived from `/home/sanand/code/calvinmap/calvin.csv`
- `mixed-media.csv`: multimodal rows derived from `/home/sanand/code/calvinmap/calvin.csv`

## Intended Schemas

- `blog-text.csv`
  - `path`, `title`, `year`, `primary_category`, `text`
- `blog-text-300.csv`
  - `path`, `title`, `year`, `primary_category`, `text`
- `calvin-images.csv`
  - `file`, `date`
- `mixed-media.csv`
  - `file`, `date`, `theme`, `place`, `person`, `headline`, `summary`

The image fixtures reference existing Calvin & Hobbes image filenames from the source repo. No image files are copied into this directory.

## Smoke Test

Run this from any directory to fetch the CLI from GitHub, read the dataset from raw GitHub, and write `index.html` in the current working directory:

```bash
uvx --from "git+https://github.com/sanand0/embedumap.git@main" embedumap https://raw.githubusercontent.com/sanand0/embedumap/main/samples/blog-text-300.csv --embedding-columns text --color-columns primary_category,year --filter-columns primary_category,year --timeline-column year
```
