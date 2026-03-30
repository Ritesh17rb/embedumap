# embedumap

`embedumap` builds a standalone `index.html` scatterplot from a CSV using Gemini embeddings, UMAP, and clustering.

## Install / run

```bash
uvx --from "git+https://github.com/sanand0/embedumap.git@main" embedumap ...
```

## Examples

Dry run:

```bash
uv run embedumap samples/blog-text.csv \
  --embedding-columns text \
  --color-columns primary_category,year \
  --filter-columns primary_category,year \
  --timeline-column year \
  --dry-run
```

Build a text map:

```bash
uv run embedumap samples/blog-text.csv \
  --embedding-columns text \
  --color-columns primary_category,year \
  --filter-columns primary_category,year \
  --timeline-column year
```

Build an image-first map:

```bash
uv run embedumap samples/calvin-images.csv \
  --image-columns file \
  --timeline-column date \
  --popup-style grid
```

## Notes

- Put `GEMINI_API_KEY` in `.env` or the environment.
- The generated HTML embeds data inline and uses direct image references when image columns are provided.
- V1 keeps the pipeline simple: no persistent embedding cache, no thumbnail generation, no sidecar JSON.
