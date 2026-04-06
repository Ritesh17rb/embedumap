# Plan: Centroid Trail Enhancements

## Context

Anand reviewed the current trails implementation and wants the centroid trail nodes to be more informative and visually expressive. The core concern is that trails currently show static dots — they need to convey **how many** points a centroid represents, **how spread out** those points are, and **what time period** they belong to. He also wants tighter control over what's visible.

---

## Tasks

### 1. Three-state trail toggle
**Current**: Trails button is on/off (trails + nodes, or nodes only).
**Wanted**: Cycle through three modes: **Trails + Nodes** (default) | **Trails Only** | **Nodes Only**.

- Modify the Trails toggle button to cycle through 3 states
- Label should update to reflect current mode (e.g., "Trails + Nodes", "Trails Only", "Nodes Only")
- "Trails + Nodes" is the default
- In "Trails Only" mode, hide all scatter points entirely
- In "Nodes Only" mode, hide trail lines/arrows but keep scatter points

**Files**: `src/embedumap/html.py` (frontend JS + button logic)

---

### 2. Filter-aware trail visibility
**Current**: When a color filter is applied (e.g., selecting "python" in category), all trails still show.
**Wanted**: Only the trail for the selected filter value should be fully visible. All other trails should fade out.

- When filters apply on the color column, match active filter values to trail `groupId`/`groupLabel`
- Fully visible trails for selected values, fade others to ~0.12 opacity
- If no filter is active, show all trails (composite view as before)

**Files**: `src/embedumap/html.py` (drawTrails function, filter state integration)

---

### 3. Proportional centroid node sizing
**Current**: All centroid dots are the same size.
**Wanted**: Size of each centroid dot should be proportional to the number of data points in that time bucket.

- Each trail point already has a `count` field (number of data points in that bucket)
- Scale the centroid dot radius based on `count` relative to min/max across all trail points
- Larger count = bigger dot, smaller count = smaller dot

**Files**: `src/embedumap/html.py` (drawTrails function, dot rendering)

---

### 4. Fuzziness / blurred boundaries based on standard deviation
**Current**: Centroid dots have hard/sharp edges.
**Wanted**: Dots should have blurred/diffuse boundaries. Higher variance in the cluster for that time period = more blur. Tight clusters = sharper dots.

- Compute standard deviation of (x, y) positions per group per time bucket in the backend
- Pass `stdX`, `stdY` (or a combined `spread`) alongside each trail point
- In the frontend, render centroid dots with a radial gradient instead of a solid fill
- Higher std = larger gradient falloff (more fuzzy), lower std = tighter gradient (sharp)

**Files**:
- `src/embedumap/core.py` (`_trails_for_group` — compute std alongside mean)
- `src/embedumap/html.py` (drawTrails — radial gradient rendering)

---

### 5. Tooltips on centroid nodes
**Current**: No tooltips on centroid trail dots.
**Wanted**: Hovering over a centroid dot should show at minimum the time period label.

- Detect mouse hover over centroid trail dots (hit test against dot positions)
- Show a tooltip with: time period label, count of points, group name
- Could reuse existing tooltip/popup infrastructure or add a lightweight canvas tooltip

**Files**: `src/embedumap/html.py` (mouse event handling, tooltip rendering)

---

### 6. Test with finer time granularity (months/days)
**Current**: Only tested with year-level data.
**Wanted**: Verify trails work correctly with month-level or day-level time data.

- Find or create a dataset with daily/monthly timestamps
- Run embedumap with `--timeline-column` pointing to a date/month column
- Verify time bucketing (`_time_bucket`, `_bucket_label`) handles months/days correctly
- Fix any issues with bucket labels, slider behavior, or trail density

**Files**:
- `src/embedumap/core.py` (`_time_bucket`, `_bucket_label` — may need finer granularity support)
- Test with a new dataset

---

## Execution Order

1. **Task 3** (proportional sizing) — quick win, data already available in `count`
2. **Task 1** (three-state toggle) — UI only, no backend changes
3. **Task 2** (filter-aware trails) — connects existing filter state to trail rendering
4. **Task 4** (fuzziness) — needs backend + frontend changes
5. **Task 5** (tooltips) — needs hit testing logic
6. **Task 6** (test with months/days) — validation, do last
