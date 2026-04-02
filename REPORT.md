# Patent Embedding & Centroid Movement — Report

## Overview

As discussed in the meeting, this report covers two deliverables:

1. **Patent corpus embedding map** — 10,000 high-citation US patent abstracts visualized using UMAP
2. **Centroid movement visualization** — tracking how technology clusters move over time on the embedding space

---

## Task 1: Patent Corpus Embedding

### Dataset

- **Source**: Google BigQuery (`patents-public-data.patents.publications`)
- **Size**: 10,000 patents
- **Coverage**: 2017–2024 (8 years)
- **Selection criteria**: US patents sorted by citation count (descending), ensuring high-importance patents
- **Average citation count**: 7,769 per patent

| Year | Patents |
|------|---------|
| 2017 | 10 |
| 2018 | 105 |
| 2019 | 1,290 |
| 2020 | 1,409 |
| 2021 | 1,646 |
| 2022 | 1,786 |
| 2023 | 1,966 |
| 2024 | 1,788 |

### Technology Categories (CPC Classification)

| Category | Count |
|----------|-------|
| Human Necessities | 6,630 |
| Electricity & Electronics | 1,872 |
| Chemistry & Metallurgy | 844 |
| Physics & Computing | 568 |
| Mechanical Engineering | 52 |
| Operations & Transport | 34 |

### Cost

| Item | Cost |
|------|------|
| Embedding 10,000 abstracts (~1.6M tokens) | ~$0.03 |
| Cluster naming (Gemini Flash) | ~$0.01 |
| Axis labeling (Gemini Flash) | ~$0.01 |
| **Total** | **~$0.05** |

Well within the $2 budget constraint.

### Pipeline

```
patents.csv (10,000 rows from BigQuery)
    → Gemini Embedding 2 Preview (768 dimensions)
    → PCA preprocessing → UMAP 2D projection
    → K-means clustering
    → LLM cluster naming + axis interpretation
    → Standalone HTML visualization (patents-map.html)
```

### How to View

Open `patents-map.html` in any browser. The visualization includes:
- **Scatterplot**: 10,000 patents projected onto 2D space
- **Color by**: cluster or category
- **Filter by**: category, year, cluster
- **Timeline slider**: filter patents by year range, with playback
- **Hover**: see patent title and details
- **Click/brush**: select patents and view details in popup
- **Bar chart**: cluster/category frequency breakdown

---

## Task 2: Centroid Movement Visualization

### What It Does

The centroid movement feature shows how groups of patents move through the embedding space over time. For each group (cluster or filter value like "category"), it computes the mean (x, y) position per year and draws a trajectory path.

### Two Modes

**Individual movement**: Click any row in the bar chart to highlight a single group's trajectory. Other trails dim to 12% opacity. This shows exactly how one technology area has shifted — for example, how "Electricity & Electronics" patents have drifted from one region of the embedding space to another over the years.

**Composite movement**: When no individual trail is highlighted, all trails are shown simultaneously. This gives a bird's-eye view of how all technology areas are evolving relative to each other.

### "Any Filter Across Time"

As requested, centroid trails work for **any filter column**, not just clusters:
- **Color by "cluster"** → see cluster centroid trails
- **Color by "category"** → see category centroid trails (e.g., how "Physics & Computing" patents move vs "Human Necessities")

Switching the color toggle automatically switches which trails are displayed.

### Visual Design

- **Colored polylines** connecting yearly centroids, using the same color as the group
- **Directional arrows** along each path showing movement direction
- **Age gradient**: older centroid dots are fainter, newer ones are brighter
- **Time labels** at start and end of each highlighted trail
- **Dot size** proportional to whether the trail is highlighted or not
- **Points dim** when trails are active, so trails stand out

### How to Use

1. Click the **"Trails"** button in the control bar to toggle trails on/off
2. Click a row in the **bar chart** to isolate one group's trajectory
3. Click the same row again to return to composite view
4. Switch **Color** between "cluster" and "category" to see different groupings' movements
5. Use the **timeline slider** to see how centroids correspond to the visible time window

### CLI Flag

```bash
embedumap patents.csv \
  --embedding-columns abstract \
  --timeline-column year \
  --color-columns category \
  --filter-columns category,year \
  --cluster-columns embeddings \
  --cluster-names \
  --centroid-trails \
  --label-columns title \
  --output patents-map.html
```

The `--centroid-trails` flag enables centroid movement computation and rendering.

---

## Files

| File | Description |
|------|-------------|
| `patents.csv` | 10,000 patent abstracts from BigQuery |
| `patents-map.html` | Generated interactive visualization |
| `src/embedumap/core.py` | Backend: centroid trail computation, batch caching |
| `src/embedumap/html.py` | Frontend: trail rendering, controls, interaction |
| `src/embedumap/cli.py` | CLI: `--centroid-trails` flag |

## Code Changes

### Backend (`core.py`)
- Added `centroid_trails` field to `BuildConfig`
- Added `compute_centroid_trails()` — computes trails for clusters AND any filter column
- Added `_trails_for_group()` — generic trail builder for any grouping function
- Added `_time_bucket()` / `_bucket_label()` — year-based time bucketing
- Improved embedding cache: flush after each batch (survives failures)
- Added 5-second delay between batches to respect free-tier rate limits

### Frontend (`html.py`)
- Added `drawTrails()` — renders polylines, arrows, dots, and labels on canvas
- Added `activeTrails()` — selects trail group based on current `colorBy` state
- Added `buildTrailsControls()` — toggle button and bar chart click-to-highlight
- Trail group switches automatically when changing color mode
- Points auto-dim when trails are active for better visibility
- URL state: `?trails=on|off` for shareable links
