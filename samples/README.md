# Sample Fixtures

These tiny CSVs are deterministic fixtures for `embedumap` development and smoke tests.

## Files

- `blog-text.csv`: text-focused rows derived from `/home/sanand/code/blog/analysis/embeddings/documents.csv`
- `calvin-images.csv`: image-focused rows derived from `/home/sanand/code/calvinmap/calvin.csv`
- `mixed-media.csv`: multimodal rows derived from `/home/sanand/code/calvinmap/calvin.csv`

## Intended Schemas

- `blog-text.csv`
  - `path`, `title`, `year`, `primary_category`, `text`
- `calvin-images.csv`
  - `file`, `date`
- `mixed-media.csv`
  - `file`, `date`, `theme`, `place`, `person`, `headline`, `summary`

The image fixtures reference existing Calvin & Hobbes image filenames from the source repo. No image files are copied into this directory.
