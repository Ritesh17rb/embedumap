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
   - Store direct image references only; do not generate thumbnails in v1

7. Implement the standalone HTML template.
   - Inline CSS, JS, and JSON data
   - Base the controls on `blogmap`
   - Base list popups on `calvinmap`
   - Base grid popups on `chart-map`
   - Keep the frontend data-driven and generic rather than blog-specific or comic-specific
   - Allow sorting by timeline or any CSV column in `table`, `list`, and `grid` modes
   - Default popup sort to timeline when present, otherwise a stable row-order fallback

8. Finish with docs and verification assets.
   - README with 3 representative commands
   - `.env` expectations
   - notes on supported modalities and v1 limits

## Default Assumptions To Confirm

- `index.html` should be fully standalone, with inline data and no sidecar JSON.
- `--image-columns` should preserve direct image references only; no thumbnail generation in v1.
- `--cluster-columns embeddings` means K-means on embedding features.
- `--cluster-columns category` should probably mean direct category labels, not K-means on one-hot metadata alone.
- Sampling should be deterministic and reproducible.
- V1 should not add persistent embedding caches unless you explicitly want them.

## Review Checklist

- Confirm the single-file portability standard you want.
- Confirm the clustering semantics you want when `embeddings` is absent from `--cluster-columns`.
- Confirm whether v1 should stay limited to text + image CLI inputs, while keeping internals ready for richer media later.
- Confirm that v1 should skip thumbnail generation entirely and show only full images when available.
- Confirm that every popup mode should expose the same sort controls across timeline and CSV columns.
- Confirm whether `--dry-run` should be the first milestone before any full build path.

# Enhancements 1

## Goal

Add one small tranche of post-v1 improvements that increase practicality without turning `embedumap` into a heavier workflow system.

## Scope

1. Add a resumable embedding cache.
2. Add audio embedding support.
3. Add LLM-based cluster naming.
4. Add a repo-hosted test text dataset with a no-clone `uvx --from ...` command path.

## Proposed Shape

### 1. Resumable embedding cache

- Keep the cache minimal and local to the output location.
- Prefer a single lightweight mutable store such as `embedumap.duckdb` over a multi-artifact cache.
- Turn the cache on by default.
- Place it next to the generated HTML output so the default path is the current working directory.
- Cache key should be based on:
  - source row identity
  - normalized embedding inputs
  - model name
  - output dimensions
  - an embedding input version string
- Store only what is needed to skip recomputation cleanly:
  - row key
  - content hash
  - embedding vector
  - optional updated timestamp for debugging
- Do not introduce a second exported cache format unless it clearly buys something. `.parquet` is optional, not required.
- Keep the first cache behavior intentionally simple:
  - reuse cached embeddings when the content hash matches
  - recompute only missing or changed rows
  - rebuild downstream UMAP/clustering outputs from the current full embedding set

### 2. Audio embedding

- Extend the internal row-content builder to accept audio columns in addition to text and image columns.
- Keep the public interface narrow:
  - add `--audio-columns`
  - add `--audio-metadata-columns` for optional text context that should be included alongside audio when the user wants it
  - use the same repeated/comma-split behavior as the other `--*-columns` options
- Resolve audio references the same way as images:
  - local file paths
  - HTTP(S) URLs
- Let Gemini handle multimodal fusion when rows contain text + image + audio together.
- Do not add audio preprocessing, transcription, segmentation, or thumbnail-like side pipelines in this tranche.
- Accept that large/unsupported audio inputs may remain a validation failure in v1.5 rather than becoming a media-processing project.

### 3. Cluster naming by LLM

- Keep clustering itself deterministic and separate from naming.
- Add a post-clustering naming pass that uses a lightweight Gemini model such as:
  - `gemini-3.1-flash-lite-preview`
  - or `gemini-3-flash-preview`
- Expose cluster naming as an explicit build flag from the start.
- For each cluster, gather a compact but informative context pack:
  - the top-N rows closest to that cluster centroid
  - enough contrasting examples from nearby clusters to disambiguate similar regions
  - the existing cluster id and size
  - a small list of salient categorical values when available
- Ask for one structured JSON response covering all clusters, not a separate request per cluster.
- The naming prompt should explicitly ask for names that are:
  - specific enough to distinguish neighboring clusters
  - broad enough to survive adding more rows later
  - short enough to fit the UI
- Keep the output shape simple and machine-checkable:
  - cluster id
  - display name
  - optional short rationale for debugging only
- Cache the naming output separately from embeddings so names can be regenerated without re-embedding.

### 4. Repo-hosted ~300-row test dataset

- Add one committed text dataset with roughly 300 rows under a stable repo path.
- Keep it easy to use as a no-clone smoke test for packaging and build behavior.
- Include:
  - the CSV itself
  - one README snippet or command example showing the exact `uvx --from ...` invocation
- The command should work from anywhere by:
  - cloning the app via `uvx --from git+https://github.com/sanand0/embedumap.git@main`
  - reading the dataset from a raw GitHub URL
  - writing `index.html` in the caller's current directory
- Prefer a text-only dataset for this path so the smoke test stays cheap, portable, and deterministic.

## Proposed Order

1. Resumable embedding cache
2. Repo-hosted ~300-row text dataset and documented `uvx --from ...` command
3. Audio embedding support
4. LLM-based cluster naming

## Why This Order

- The cache improves every subsequent workflow and lowers testing cost immediately.
- The repo-hosted dataset gives a stable public verification path for packaging and CLI behavior.
- Audio embedding extends the existing content builder cleanly once caching is in place.
- Cluster naming should come last because it depends on stable clustering outputs and introduces an extra model layer.

## Default Assumptions To Confirm

- A single-file `.duckdb` cache is preferable to a `.duckdb + .parquet` cache pair.
- The cache should be enabled by default.
- The cache should live next to the output HTML, which usually means the current working directory.
- Cache reuse should be row-level only; downstream UMAP/clustering can still be recomputed from the current full embedding matrix.
- `--audio-columns` should follow the exact ergonomics of the existing `--image-columns` and `--embedding-columns`.
- The first public audio support can be "pass file/URL through to Gemini if valid" without custom preprocessing, with optional `--audio-metadata-columns` when the user wants extra text context.
- Cluster naming should be exposed as a build flag from the start, while remaining a separate post-processing pass.
- The repo-hosted ~300-row dataset should be text-only, committed to GitHub, and referenced via a raw GitHub URL in docs/examples.
- Cluster names should stay reasonably short while still disambiguating similar neighboring clusters.
- The public ~300-row dataset only needs to be representative and convenient, not hand-curated.

## Review Checklist For Enhancements 1

- Confirm that the cache should stay minimal and elegant, even if that means recomputing UMAP/clustering after embedding reuse.
- Confirm that a single `.duckdb` cache is the preferred starting point.
- Confirm that the cache should be on by default and stored next to the output HTML.
- Confirm that audio support should begin with `--audio-columns` plus optional `--audio-metadata-columns`, without transcription or segmentation features.
- Confirm that cluster naming should be a separate post-processing pass, not mixed into clustering itself.
- Confirm that cluster naming should be available behind a build flag from the start.
- Confirm that one structured JSON naming response across all clusters is the right shape.
- Confirm that cluster names should optimize for brevity and nearby-cluster disambiguation together.
- Confirm that the ~300-row public smoke-test dataset should be text-only and stored in the repo.
- Confirm that the no-clone verification path should use `uvx --from ...` plus a raw GitHub CSV URL.
