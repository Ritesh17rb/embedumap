# Embedumap Notes

## What I learned from the references

The three reference codebases all converge on the same useful pattern:

- Compute embeddings, UMAP coordinates, and clusters before the browser sees the data.
- Keep the browser focused on rendering, filtering, brushing, hover, and popup interactions.
- Use canvas for the scatterplot and lightweight DOM for controls and popups.
- Keep selection UX simple:
  - hover for a compact tooltip
  - click for one row
  - brush for many rows
- Treat popup rendering as the main place where all row detail lives.

What should be carried into `embedumap`:

- `blogmap`
  - best baseline for generic text datasets
  - color toggles, dropdown filters, timeline slider, sortable table popup
- `calvinmap`
  - best baseline for list/card popups and date-ordered media browsing
  - good example of stable server-side analysis followed by a small browser payload
- `chart-map`
  - best baseline for image-first grid popup behavior
  - best baseline for grid popup layout, but not for thumbnail generation in v1

## Current external constraints

Official Gemini docs currently say:

- `gemini-embedding-2-preview` is the latest Gemini multimodal embedding model.
- It supports text, image, video, audio, and PDF input in one embedding space.
- Its latest model-page update shown in the docs is November 2025.
- It supports flexible output dimensionality from 128 to 3072, with 768, 1536, and 3072 recommended.
- Non-3072 outputs should be normalized before downstream similarity work.
- `gemini-embedding-001` is still available, but it is text-only and its embedding space is incompatible with `gemini-embedding-2-preview`.

This matters because the requested default of `gemini-embedding-2-preview` is still aligned with the current official docs, and it lets the implementation stay generic internally even if v1 only exposes text and image columns.

## Proposed v1 scope

Keep the public CLI narrow, but design the pipeline to grow without rewrites.

Public v1 inputs:

- positional CSV path or URL
- `--embedding-columns`
- `--image-columns`
- `--color-columns`
- `--filter-columns`
- `--timeline-column`
- `--cluster-columns`
- `--label-column`
- `--popup-style table|grid|list`
- `--model`
- `--dimensions`
- `--sample`
- `--dry-run`

Internal design choices:

- One row = one embedding unit.
- Text columns are merged into one text block with light field labels.
- Image columns are resolved from local paths or remote URLs and attached as image parts.
- Mixed rows use one multimodal Gemini embedding call so Gemini performs the fusion.
- The browser gets only:
  - row metadata
  - 2D coordinates
  - derived cluster/color/filter/timeline values
  - popup-safe row payload
  - direct image references when image columns are present
- The browser does not run UMAP or clustering.

## Proposed defaults

- Output file: `./index.html`
- Model: `gemini-embedding-2-preview`
- Dimensions: `768`
- Label columns default:
  - first embedding column if present
  - else first image column basename/URL tail
  - else row number
- Color dimensions default:
  - derived `cluster` only when no `--color-columns` are provided
- Cluster default:
  - `--cluster-columns embeddings`
- Timeline:
  - only shown when `--timeline-column` parses successfully for enough rows
- Sampling:
  - deterministic random sample with a fixed seed unless you prefer first-N behavior

## Proposed clustering semantics

This is the biggest ambiguity in the current spec.

Recommended interpretation:

- `--cluster-columns embeddings`
  - run K-means on embedding-derived features
- `--cluster-columns embeddings,category`
  - run K-means on embeddings plus encoded category features
- `--cluster-columns category`
  - do not run K-means
  - use the category values directly as cluster labels

Why this interpretation is the cleanest:

- It matches your default example.
- It matches your mixed example with `embeddings,category`.
- It also makes the phrase "use those as the cluster labels instead of K-means" coherent when `embeddings` is absent.

## Single-file output implications

The `single index.html` requirement has real consequences.

For v1, you explicitly asked to drop thumbnails.

My recommendation:

- inline all JSON data
- inline CSS and JS
- keep direct image references only
- keep original raw CSV values visible in the popup
- avoid a sidecar `embeddings.min.json`

That means local image datasets will only display full images when the referenced files are directly reachable from the browser context.

## What I would deliberately not do in v1

- No resumable embedding cache yet
- No cluster naming by LLM yet
- No hierarchical broad/fine clustering yet
- No audio/video/PDF-specific public flags yet
- No multi-file build output
- No browser-side fetching of a separate JSON payload
- No thumbnail generation pipeline

These can all come later if needed, but none are required for a clean first release.

## First milestone I recommend

Implement `--dry-run` before the full build path.

It should report:

- input source and row count
- resolved column groups
- rows with usable embedding content
- rows skipped for missing content
- timeline parse success rate
- filter/color cardinalities
- whether image references look usable as-is
- estimated Gemini request count
- estimated output size risk
- the exact defaults that will be applied

That gives you a fast way to validate the product shape on 3 or 4 representative CSVs before paying any embedding cost.

## Questions for you

1. When `--cluster-columns` does not include `embeddings`, do you want direct labels from those columns, or K-means over encoded metadata anyway?
2. Do you want the generated `index.html` to be considered acceptable even though local-image previews depend on those image files being directly reachable by the browser?
3. Is it acceptable for v1 to expose only text and image columns publicly, while keeping the internal row-content builder generic enough for audio/video/PDF later?
4. Should `--sample N` mean a deterministic random sample, or literally the first `N` rows?
5. Do you want an extra `--output` option in v1, or should the tool always write `index.html` in the current directory?
6. Is a compact hover tooltip with truncated field values acceptable if the popup always shows the full row, and every popup mode has user-selectable sorting across timeline and CSV columns?
7. Do you want cluster count fixed internally for v1, or do you already know you want a public `--clusters` option?

## How to review the plan

- Verify that the plan keeps the public CLI narrow instead of turning into a generic data-processing framework.
- Verify that one row equals one embedding unit is the right mental model for your datasets.
- Verify that mixed text + image rows should be fused by Gemini in one request, not by custom weighting logic.
- Verify that `--cluster-columns` semantics are correct, especially the non-`embeddings` case.
- Verify that `cluster` should always exist as a derived color/filter dimension even if not explicitly listed in the CSV.
- Verify that `--dry-run` is the right first milestone before any full implementation.
- Verify that a single-file deliverable really means no sidecar JSON, even though v1 will not inline thumbnails.
- Verify that the proposed defaults are acceptable:
  - model `gemini-embedding-2-preview`
  - dimensions `768`
  - output `index.html`
  - deterministic sampling
- Verify that v1 should stay intentionally incomplete in these ways:
  - no persistent cache
  - no audio/video/PDF public flags
  - no LLM-generated cluster names
  - no hierarchical cluster model
- Verify that the three popup modes should behave this way:
  - `table`: sortable full-row table
  - `list`: one selected row per card, with the same sort controls as table mode
  - `grid`: image-first cards with metadata beneath, with the same sort controls as table mode
- Verify that the first representative datasets to test after approval should be:
  - a text-only blog or papers CSV
  - an image-heavy CSV with local filenames
  - a mixed metadata CSV with text, images, year/category, and a timeline column

## Enhancements 1 assumptions

- The cache should stay intentionally small and local, preferably one `.duckdb` file.
- The cache should be on by default and live next to the output HTML.
- Reusing row-level embeddings is the main win; refitting downstream projections is acceptable in the first cache version.
- Audio support should start with file/URL passthrough to Gemini, not a custom media-processing pipeline, with optional audio metadata columns when needed.
- Cluster naming should be exposed as a build flag and remain separate from clustering so the core layout stays deterministic.
- Cluster names should stay reasonably short while still disambiguating nearby clusters.
- The first public smoke-test dataset for the GitHub-hosted `uvx --from ...` path should be text-only.
- The public ~300-row test dataset only needs to be representative and convenient, not hand-curated.

## How to review Enhancements 1

- Verify that the resumable cache stays lightweight:
  - ideally one `.duckdb`
  - no extra cache formats unless they clearly add value
- Verify that the cache should be on by default and written next to the output HTML.
- Verify that row-level cache reuse is sufficient for the first pass, even if UMAP/clustering are recomputed afterward.
- Verify that `--audio-columns` should mirror the ergonomics of the existing `--embedding-columns` and `--image-columns`.
- Verify that optional `--audio-metadata-columns` is the right level of extra control for audio rows.
- Verify that audio support should remain narrow:
  - local files and HTTP(S) URLs
  - no transcription pipeline
  - no segmentation/chunking system in this tranche
- Verify that cluster naming should be a separate post-clustering pass using a lightweight Gemini model.
- Verify that cluster naming should be exposed as an explicit build flag from the start.
- Verify that the naming input should use top-N centroid-nearest rows plus nearby-cluster contrast, rather than sending whole clusters.
- Verify that the naming output should be structured JSON with one entry per cluster.
- Verify that cluster names should optimize for:
  - reasonable brevity
  - disambiguation from similar clusters
  - UI-friendly length
- Verify that the public ~300-row dataset should be:
  - committed to the repo
  - text-only
  - accessible by raw GitHub URL
  - documented with a copy-pasteable `uvx --from ...` command
- Verify the proposed order:
  - cache first
  - public smoke-test dataset second
  - audio support third
  - cluster naming fourth
