# Embedumap Plan

## Goal

Build a packaged CLI named `embedumap` that can be run via:

```bash
uvx --from "git+https://github.com/sanand0/embedumap.git" embedumap ...
```

The command should read a local or remote CSV, generate Gemini-based embeddings, run PCA + UMAP + clustering, and write a single `index.html` file containing the full interactive visualization.

## Principles

- Keep v1 one-shot and elegant. No workflow engine, no background services, no multi-file web app.
- Emit one browser-openable HTML file with inline CSS, JS, and data.
- Reuse the interaction model from `blogmap`, `calvinmap`, and `chart-map`, but collapse it into one generic template.
- Let Gemini handle multimodal fusion. The CLI should assemble row content, not invent modality-specific feature engineering.
- Design the internals so audio/video/PDF can be added later without redesigning the pipeline, even if the first public CLI only exposes text and image columns.

## Planned Shape

1. Package the project with `pyproject.toml`, a `src/embedumap/` module, and a `[project.scripts]` entry point so `uvx --from ... embedumap` works cleanly.
2. Implement a small CLI around a single pipeline: load CSV, validate config, optionally sample, embed rows, reduce dimensions, cluster, render HTML.
3. Support repeated comma-separated `--*-columns` values and repeated flags by normalizing them into one ordered list per option.
4. Treat each CSV row as one embedding unit:
   - text columns become one merged text payload
   - image columns become one or more image parts
   - mixed text + image rows become one multimodal Gemini embedding request
5. Use Gemini Embedding 2 Preview as the default because current official docs say it supports text, image, video, audio, and PDF in one embedding space.
6. Normalize non-3072 embeddings before downstream similarity, clustering, and UMAP.
7. Run a fixed deterministic analysis stack server-side:
   - sample if requested
   - Gemini embeddings
   - optional PCA
   - UMAP to 2D
   - K-means or direct-label clustering depending on `--cluster-columns`
8. Generate one standalone HTML file with:
   - canvas scatter plot
   - hover tooltip
   - click/brush selection
   - filters
   - color toggles
   - optional timeline range slider
   - one popup mode chosen at build time: `table`, `list`, or `grid`

## Implementation Steps

1. Scaffold packaging and CLI plumbing.
   - Add `pyproject.toml`
   - Add `src/embedumap/cli.py`
   - Add `src/embedumap/__init__.py`
   - Choose a minimal dependency set

2. Build config parsing and validation.
   - Parse local path or URL CSV input
   - Normalize repeated and comma-separated column args
   - Validate missing columns, duplicate column names, and conflicting choices
   - Resolve defaults for labels, colors, clustering, and output path

3. Implement `--dry-run` first.
   - Load the CSV
   - Resolve local vs remote media references
   - Report row counts, usable rows, selected columns, unique counts for filters/colors, timeline parse success, and estimated output size risks
   - Do not call Gemini or write HTML

4. Implement row content assembly.
   - Merge text columns with simple field labels
   - Resolve image columns from local files or URLs
   - Create one Gemini content payload per row
   - Keep the loader generic enough for future audio/video/PDF support

5. Implement embedding and analysis.
   - Batch Gemini requests
   - Normalize embeddings
   - Apply deterministic PCA + UMAP
   - Derive clusters using the agreed semantics for `--cluster-columns`

6. Implement visualization payload generation.
   - Store 2D coordinates
   - Store derived cluster/color/filter/timeline metadata
   - Store raw row cells for popups
   - Store truncated label and tooltip display text separately from raw values
   - Inline lightweight preview thumbnails for image-driven popups when needed

7. Implement the standalone HTML template.
   - Inline CSS, JS, and JSON data
   - Base the controls on `blogmap`
   - Base list popups on `calvinmap`
   - Base grid popups on `chart-map`
   - Keep the frontend data-driven and generic rather than blog-specific or comic-specific

8. Finish with docs and verification assets.
   - README with 3 representative commands
   - `.env` expectations
   - notes on supported modalities and v1 limits

## Default Assumptions To Confirm

- `index.html` should be fully standalone, with inline data and no sidecar JSON.
- `--image-columns` should inline preview thumbnails into the HTML so local image datasets still work when the HTML is opened directly.
- `--cluster-columns embeddings` means K-means on embedding features.
- `--cluster-columns category` should probably mean direct category labels, not K-means on one-hot metadata alone.
- Sampling should be deterministic and reproducible.
- V1 should not add persistent embedding caches unless you explicitly want them.

## Review Checklist

- Confirm the single-file portability standard you want.
- Confirm the clustering semantics you want when `embeddings` is absent from `--cluster-columns`.
- Confirm whether v1 should stay limited to text + image CLI inputs, while keeping internals ready for richer media later.
- Confirm whether inline thumbnails are acceptable for image datasets even if they increase HTML size.
- Confirm whether `--dry-run` should be the first milestone before any full build path.
