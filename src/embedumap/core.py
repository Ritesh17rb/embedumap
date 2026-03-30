"""Core pipeline for embedumap."""

from __future__ import annotations

import io
import math
import mimetypes
import os
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import httpx
import numpy as np
import pandas as pd
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from PIL import Image
from rich.console import Console
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import OneHotEncoder
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

console = Console()
DEFAULT_MODEL = "gemini-embedding-2-preview"
DEFAULT_DIMENSIONS = 768
DEFAULT_BATCH_SIZE = 8
MAX_LABEL_CHARS = 140
MAX_TOOLTIP_CHARS = 140
UMAP_NEIGHBORS = 20
UMAP_MIN_DIST = 0.15


@dataclass(slots=True)
class CsvSource:
    """Resolved CSV source and media bases."""

    label: str
    frame: pd.DataFrame
    csv_path: Path | None
    csv_url: str | None


@dataclass(slots=True)
class BuildConfig:
    """Normalized CLI configuration."""

    csv_input: str
    output_path: Path
    embedding_columns: list[str]
    image_columns: list[str]
    color_columns: list[str]
    filter_columns: list[str]
    cluster_columns: list[str]
    label_columns: list[str]
    timeline_column: str | None
    popup_style: str
    model: str
    dimensions: int
    sample: int | None
    dry_run: bool


@dataclass(slots=True)
class ImageInput:
    """One image reference for embedding and popup display."""

    raw_value: str
    display_url: str
    local_path: Path | None
    remote_url: str | None
    exists: bool


@dataclass(slots=True)
class RowRecord:
    """Prepared row used for embedding, analysis, and rendering."""

    row_index: int
    raw: dict[str, str]
    tooltip: dict[str, str]
    label: str
    text_payload: str
    images: list[ImageInput]
    timeline_text: str | None
    timeline_ms: int | None


def split_option_values(values: list[str]) -> list[str]:
    """Split repeated comma-delimited option values while preserving order."""

    flattened: list[str] = []
    seen: set[str] = set()
    for value in values:
        for item in str(value).split(","):
            cleaned = item.strip()
            if not cleaned or cleaned in seen:
                continue
            flattened.append(cleaned)
            seen.add(cleaned)
    return flattened


def truncate(value: str, limit: int) -> str:
    """Clamp a display value without mutating the raw row."""

    text = str(value).strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def is_http_url(value: str) -> bool:
    """Return True when the value is an HTTP(S) URL."""

    return urlparse(value).scheme in {"http", "https"}


def is_file_url(value: str) -> bool:
    """Return True when the value is a file URI."""

    return urlparse(value).scheme == "file"


def filename_tail(value: str) -> str:
    """Return the last filename-like path segment for labels."""

    if is_http_url(value) or is_file_url(value):
        return Path(unquote(urlparse(value).path)).name or value
    return Path(value).name or value


def load_csv_source(csv_input: str) -> CsvSource:
    """Load a local or remote CSV into a normalized string dataframe."""

    if is_http_url(csv_input):
        with httpx.Client(follow_redirects=True, timeout=60) as client:
            response = client.get(csv_input)
            response.raise_for_status()
        frame = pd.read_csv(io.StringIO(response.text), dtype=str, keep_default_na=False).fillna("")
        return CsvSource(label=str(response.url), frame=frame, csv_path=None, csv_url=str(response.url))

    csv_path = Path(csv_input).expanduser().resolve()
    frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False).fillna("")
    return CsvSource(label=str(csv_path), frame=frame, csv_path=csv_path, csv_url=None)


def validate_columns(frame: pd.DataFrame, columns: list[str], *, allow_special: set[str] | None = None) -> None:
    """Raise on missing columns while allowing explicit virtual names."""

    allow_special = allow_special or set()
    missing = [column for column in columns if column not in allow_special and column not in frame.columns]
    if missing:
        sample = ", ".join(missing)
        raise ValueError(f"Unknown CSV column(s): {sample}")


def apply_sample(frame: pd.DataFrame, sample: int | None) -> pd.DataFrame:
    """Apply a deterministic sample while preserving original row order."""

    frame = frame.copy()
    frame["_row_index"] = np.arange(len(frame))
    if sample is None or sample >= len(frame):
        return frame.reset_index(drop=True)
    sampled = frame.sample(n=sample, random_state=42).sort_values("_row_index")
    return sampled.reset_index(drop=True)


def row_text_payload(row: pd.Series, columns: list[str]) -> str:
    """Build the merged text payload for one row."""

    parts = [f"{column}: {str(row[column]).strip()}" for column in columns if str(row[column]).strip()]
    return "\n\n".join(parts)


def resolve_image_input(source: CsvSource, raw_value: str) -> ImageInput | None:
    """Resolve one raw image cell into browser and embedding references."""

    value = str(raw_value).strip()
    if not value:
        return None
    if is_http_url(value):
        return ImageInput(raw_value=value, display_url=value, local_path=None, remote_url=value, exists=True)
    if is_file_url(value):
        path = Path(unquote(urlparse(value).path))
        return ImageInput(
            raw_value=value,
            display_url=value,
            local_path=path,
            remote_url=None,
            exists=path.exists(),
        )
    if source.csv_url:
        joined = urljoin(source.csv_url, value)
        return ImageInput(raw_value=value, display_url=joined, local_path=None, remote_url=joined, exists=True)
    if not source.csv_path:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (source.csv_path.parent / path).resolve()
    return ImageInput(
        raw_value=value,
        display_url=path.as_uri(),
        local_path=path,
        remote_url=None,
        exists=path.exists(),
    )


def timeline_values(frame: pd.DataFrame, timeline_column: str | None) -> pd.Series | None:
    """Parse the optional timeline column into UTC milliseconds."""

    if not timeline_column:
        return None
    parsed = pd.to_datetime(frame[timeline_column], utc=True, errors="coerce")
    return parsed


def default_label(row: pd.Series, embedding_columns: list[str], image_columns: list[str]) -> str:
    """Derive a row label when the user did not choose one explicitly."""

    if embedding_columns:
        value = str(row[embedding_columns[0]]).strip()
        if value:
            return truncate(value, MAX_LABEL_CHARS)
    if image_columns:
        value = str(row[image_columns[0]]).strip()
        if value:
            return filename_tail(value)
    return f"Row {int(row['_row_index']) + 1}"


def prepare_rows(source: CsvSource, config: BuildConfig) -> tuple[list[RowRecord], dict[str, object]]:
    """Normalize rows, resolve labels, and collect image references."""

    frame = apply_sample(source.frame, config.sample)
    validate_columns(frame, config.embedding_columns + config.image_columns)
    validate_columns(frame, config.color_columns + config.filter_columns + config.label_columns)
    validate_columns(frame, [value for value in config.cluster_columns if value != "embeddings"], allow_special={"embeddings"})
    if config.timeline_column:
        validate_columns(frame, [config.timeline_column])

    parsed_timeline = timeline_values(frame, config.timeline_column)
    records: list[RowRecord] = []
    skipped_rows = 0
    missing_local_images = 0
    remote_image_rows = 0

    for idx, row in frame.iterrows():
        raw = {column: str(row[column]) for column in source.frame.columns}
        tooltip = {column: truncate(raw[column], MAX_TOOLTIP_CHARS) for column in source.frame.columns}
        text_payload = row_text_payload(row, config.embedding_columns)
        images = [resolved for column in config.image_columns if (resolved := resolve_image_input(source, raw[column]))]
        if images:
            remote_image_rows += sum(image.remote_url is not None for image in images)
            missing_local_images += sum(image.local_path is not None and not image.exists for image in images)
        label = truncate(
            " | ".join(str(row[column]).strip() for column in config.label_columns if str(row[column]).strip())
            or default_label(row, config.embedding_columns, config.image_columns),
            MAX_LABEL_CHARS,
        )
        timeline_text = None
        timeline_ms = None
        if parsed_timeline is not None and not pd.isna(parsed_timeline.iloc[idx]):
            timestamp = parsed_timeline.iloc[idx]
            timeline_text = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            timeline_ms = int(timestamp.value // 1_000_000)

        has_content = bool(text_payload) or any(image.exists or image.remote_url for image in images)
        if not has_content:
            skipped_rows += 1
            continue
        records.append(
            RowRecord(
                row_index=int(row["_row_index"]),
                raw=raw,
                tooltip=tooltip,
                label=label,
                text_payload=text_payload,
                images=images,
                timeline_text=timeline_text,
                timeline_ms=timeline_ms,
            )
        )

    timeline_non_empty = int(frame[config.timeline_column].astype(str).str.strip().ne("").sum()) if config.timeline_column else 0
    timeline_valid = int(parsed_timeline.notna().sum()) if parsed_timeline is not None else 0
    report = {
        "source": source.label,
        "total_rows": int(len(frame)),
        "usable_rows": int(len(records)),
        "skipped_rows": int(skipped_rows),
        "timeline_non_empty": timeline_non_empty,
        "timeline_valid": timeline_valid,
        "missing_local_images": int(missing_local_images),
        "remote_image_rows": int(remote_image_rows),
        "frame": frame,
    }
    return records, report


def dry_run_report(source: CsvSource, config: BuildConfig, records: list[RowRecord], report: dict[str, object]) -> None:
    """Print a compact dry-run summary."""

    frame = report["frame"]
    color_counts = {column: int(frame[column].astype(str).fillna("").nunique(dropna=False)) for column in config.color_columns}
    filter_counts = {column: int(frame[column].astype(str).fillna("").nunique(dropna=False)) for column in config.filter_columns}
    cluster_mode = "kmeans" if "embeddings" in config.cluster_columns else "direct-label"
    console.print(f"Source: {report['source']}")
    console.print(
        f"Rows: {report['total_rows']} sampled, {report['usable_rows']} usable, {report['skipped_rows']} skipped"
    )
    console.print(f"Embedding columns: {config.embedding_columns or ['(none)']}")
    console.print(f"Image columns: {config.image_columns or ['(none)']}")
    console.print(f"Color columns: {config.color_columns or ['(cluster only)']}")
    console.print(f"Filter columns: {config.filter_columns or ['(cluster only)']}")
    console.print(f"Cluster columns: {config.cluster_columns} ({cluster_mode})")
    console.print(f"Label columns: {config.label_columns or ['(derived default)']}")
    if config.timeline_column:
        console.print(
            f"Timeline: {config.timeline_column} ({report['timeline_valid']}/{report['timeline_non_empty']} parseable)"
        )
    if report["missing_local_images"]:
        console.print(f"Missing local image references: {report['missing_local_images']}")
    if report["remote_image_rows"]:
        console.print(f"Rows with remote image URLs: {report['remote_image_rows']}")
    if color_counts:
        console.print(f"Color cardinalities: {color_counts}")
    if filter_counts:
        console.print(f"Filter cardinalities: {filter_counts}")
    console.print(f"Output: {config.output_path}")


def image_bytes(image: ImageInput) -> tuple[bytes, str]:
    """Fetch one image payload and mime type for Gemini embedding."""

    if image.local_path:
        if not image.local_path.exists():
            raise FileNotFoundError(f"Missing image file: {image.local_path}")
        mime_type = mimetypes.guess_type(image.local_path.name)[0] or "application/octet-stream"
        return normalized_image_bytes(image.local_path.read_bytes(), mime_type)

    if not image.remote_url:
        raise FileNotFoundError(f"Could not resolve image reference: {image.raw_value}")
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        response = client.get(image.remote_url)
        response.raise_for_status()
    mime_type = response.headers.get("content-type", "").split(";")[0] or mimetypes.guess_type(image.remote_url)[0] or "application/octet-stream"
    return normalized_image_bytes(response.content, mime_type)


def normalized_image_bytes(data: bytes, mime_type: str) -> tuple[bytes, str]:
    """Convert image inputs into a Gemini-friendly PNG payload."""

    if not mime_type.startswith("image/"):
        return data, mime_type
    with Image.open(io.BytesIO(data)) as image:
        converted = image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
        buffer = io.BytesIO()
        converted.save(buffer, format="PNG")
        return buffer.getvalue(), "image/png"


def build_content(record: RowRecord) -> types.Content:
    """Create one Gemini content payload for a row."""

    parts: list[types.Part] = []
    if record.text_payload:
        parts.append(types.Part.from_text(text=record.text_payload))
    for image in record.images:
        data, mime_type = image_bytes(image)
        parts.append(types.Part.from_bytes(data=data, mime_type=mime_type))
    if not parts:
        raise ValueError(f"Row {record.row_index} has no embeddable content")
    return types.Content(parts=parts)


def normalize_vectors(matrix: np.ndarray) -> np.ndarray:
    """L2-normalize vectors for cosine-friendly downstream analysis."""

    if matrix.size == 0:
        return matrix
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe = np.where(norms == 0, 1.0, norms)
    return matrix / safe


@retry(
    retry=retry_if_exception_type(genai_errors.ServerError),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    stop=stop_after_attempt(6),
    reraise=True,
)
def embed_batch_once(
    client: genai.Client,
    model: str,
    dimensions: int,
    contents: list[types.Content],
) -> np.ndarray:
    """Embed one batch via Gemini."""

    response = client.models.embed_content(
        model=model,
        contents=contents,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=dimensions,
        ),
    )
    vectors = np.array([list(item.values) for item in response.embeddings], dtype=np.float32)
    return normalize_vectors(vectors)


def embed_records(records: list[RowRecord], model: str, dimensions: int) -> np.ndarray:
    """Embed all prepared rows with bounded retries and progress logging."""

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY in the environment or .env before building")
    client = genai.Client(api_key=api_key)
    batches: list[np.ndarray] = []
    for start in range(0, len(records), DEFAULT_BATCH_SIZE):
        batch = records[start : start + DEFAULT_BATCH_SIZE]
        console.print(f"Embedding rows {start + 1}-{start + len(batch)} of {len(records)}...")
        contents = [build_content(record) for record in batch]
        delay = 4
        for attempt in range(6):
            try:
                batches.append(embed_batch_once(client, model, dimensions, contents))
                break
            except genai_errors.ClientError as exc:
                message = str(exc)
                if "429" not in message and "RESOURCE_EXHAUSTED" not in message:
                    raise
                if attempt == 5:
                    raise
                console.print(f"Rate limited. Sleeping {delay}s before retry {attempt + 1}/6.")
                import time

                time.sleep(delay)
                delay = min(delay * 2, 120)
    return np.vstack(batches) if batches else np.empty((0, dimensions), dtype=np.float32)


def fallback_coords(vectors: np.ndarray) -> np.ndarray:
    """Return a deterministic 2D fallback when UMAP cannot fit."""

    count = len(vectors)
    if count == 0:
        return np.empty((0, 2), dtype=np.float32)
    if count == 1:
        return np.zeros((1, 2), dtype=np.float32)
    if count == 2:
        return np.array([[-1.0, 0.0], [1.0, 0.0]], dtype=np.float32)
    pca = PCA(n_components=min(2, vectors.shape[1]), random_state=42)
    coords = pca.fit_transform(vectors).astype(np.float32)
    if coords.shape[1] == 1:
        coords = np.column_stack([coords[:, 0], np.zeros(len(coords), dtype=np.float32)])
    return coords


def project_umap(vectors: np.ndarray) -> np.ndarray:
    """Project embeddings into a 2D layout."""

    count = len(vectors)
    if count < 5:
        return fallback_coords(vectors)
    pca_components = min(50, count - 1, vectors.shape[1])
    pca = PCA(n_components=pca_components, random_state=42)
    reduced = pca.fit_transform(vectors).astype(np.float32)
    import umap

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=min(UMAP_NEIGHBORS, max(2, count - 1)),
        min_dist=UMAP_MIN_DIST,
        metric="cosine",
        random_state=42,
    )
    return reducer.fit_transform(reduced).astype(np.float32)


def cluster_count(count: int) -> int:
    """Choose a modest default cluster count without exposing a flag yet."""

    if count <= 1:
        return 1
    if count < 9:
        return 2
    return min(12, max(2, round(math.sqrt(count))))


def reorder_labels(raw_labels: np.ndarray) -> tuple[np.ndarray, dict[int, int]]:
    """Reassign cluster ids by descending size."""

    counts = pd.Series(raw_labels).value_counts().sort_values(ascending=False)
    mapping = {int(label): idx for idx, label in enumerate(counts.index)}
    mapped = np.array([mapping[int(label)] for label in raw_labels], dtype=np.int32)
    return mapped, mapping


def direct_cluster_labels(records: list[RowRecord], columns: list[str]) -> tuple[np.ndarray, dict[int, str]]:
    """Use one or more CSV columns directly as cluster labels."""

    labels = []
    for record in records:
        parts = []
        for column in columns:
            value = record.raw[column].strip() or "(blank)"
            parts.append(value if len(columns) == 1 else f"{column}={value}")
        labels.append(" | ".join(parts))
    series = pd.Series(labels)
    codes, uniques = pd.factorize(series, sort=False)
    mapped, mapping = reorder_labels(codes.astype(np.int32))
    label_map = {new: str(uniques[old]) for old, new in mapping.items()}
    return mapped, label_map


def kmeans_clusters(
    records: list[RowRecord],
    vectors: np.ndarray,
    columns: list[str],
) -> tuple[np.ndarray, dict[int, str]]:
    """Cluster on embeddings plus optional one-hot metadata."""

    blocks: list[np.ndarray] = []
    if "embeddings" in columns or not columns:
        embed_components = min(32, len(vectors) - 1, vectors.shape[1]) if len(vectors) > 2 else vectors.shape[1]
        if embed_components and embed_components < vectors.shape[1]:
            pca = PCA(n_components=embed_components, random_state=42)
            embed_block = pca.fit_transform(vectors).astype(np.float32)
        else:
            embed_block = vectors.astype(np.float32)
        blocks.append(normalize_vectors(embed_block))

    meta_columns = [column for column in columns if column != "embeddings"]
    if meta_columns:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=np.float32)
        encoded = encoder.fit_transform([[record.raw[column] for column in meta_columns] for record in records])
        blocks.append(0.45 * normalize_vectors(encoded))

    feature_matrix = np.hstack(blocks) if len(blocks) > 1 else blocks[0]
    if len(records) < 2:
        labels = np.zeros(len(records), dtype=np.int32)
    else:
        model = KMeans(n_clusters=cluster_count(len(records)), random_state=42, n_init="auto")
        labels = model.fit_predict(feature_matrix)
    mapped, _ = reorder_labels(labels)
    names = {cluster_id: f"Cluster {cluster_id + 1}" for cluster_id in sorted(set(mapped.tolist()))}
    return mapped, names


def analyze_records(records: list[RowRecord], config: BuildConfig) -> tuple[np.ndarray, np.ndarray, dict[int, str]]:
    """Embed, project, and cluster the prepared rows."""

    vectors = embed_records(records, config.model, config.dimensions)
    coords = project_umap(vectors)
    if config.cluster_columns == ["embeddings"] or "embeddings" in config.cluster_columns:
        cluster_ids, cluster_labels = kmeans_clusters(records, vectors, config.cluster_columns)
    else:
        cluster_ids, cluster_labels = direct_cluster_labels(records, config.cluster_columns)
    return coords, cluster_ids, cluster_labels


def build_payload(
    source: CsvSource,
    config: BuildConfig,
    records: list[RowRecord],
    coords: np.ndarray,
    cluster_ids: np.ndarray,
    cluster_labels: dict[int, str],
) -> dict[str, object]:
    """Build the browser payload consumed by the standalone HTML."""

    filter_columns = list(dict.fromkeys([*config.filter_columns, "cluster"]))
    color_columns = list(dict.fromkeys([*config.color_columns, "cluster"]))
    sort_columns = ["_row_index", *([config.timeline_column] if config.timeline_column else []), *source.frame.columns.tolist()]
    sort_columns = list(dict.fromkeys(column for column in sort_columns if column))

    rows: list[dict[str, object]] = []
    for idx, record in enumerate(records):
        cluster_id = int(cluster_ids[idx])
        cluster_label = cluster_labels[cluster_id]
        row_payload = {
            "id": int(record.row_index),
            "x": round(float(coords[idx, 0]), 6),
            "y": round(float(coords[idx, 1]), 6),
            "label": record.label,
            "timelineText": record.timeline_text,
            "timelineMs": record.timeline_ms,
            "clusterId": cluster_id,
            "clusterLabel": cluster_label,
            "images": [image.display_url for image in record.images],
            "raw": record.raw,
            "tooltip": record.tooltip,
            "colors": {
                **{column: record.raw[column].strip() or "(blank)" for column in config.color_columns},
                "cluster": cluster_label,
            },
            "filters": {
                **{column: record.raw[column].strip() or "(blank)" for column in config.filter_columns},
                "cluster": cluster_label,
            },
        }
        rows.append(row_payload)

    x_values = [row["x"] for row in rows] or [0.0]
    y_values = [row["y"] for row in rows] or [0.0]
    cluster_counts = Counter(int(cluster_id) for cluster_id in cluster_ids.tolist())
    timeline_values = [row["timelineMs"] for row in rows if row["timelineMs"] is not None]

    return {
        "title": f"embedumap · {Path(source.label).name}",
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "popupStyle": config.popup_style,
        "source": source.label,
        "columns": source.frame.columns.tolist(),
        "imageColumns": config.image_columns,
        "colorColumns": color_columns,
        "filterColumns": filter_columns,
        "sortColumns": sort_columns,
        "defaultSort": config.timeline_column or "_row_index",
        "timelineColumn": config.timeline_column,
        "timelineMin": min(timeline_values) if timeline_values else None,
        "timelineMax": max(timeline_values) if timeline_values else None,
        "clusters": [
            {"id": cluster_id, "label": cluster_labels[cluster_id], "count": cluster_counts[cluster_id]}
            for cluster_id in sorted(cluster_labels)
        ],
        "rows": rows,
        "xDomain": [round(float(min(x_values)), 6), round(float(max(x_values)), 6)],
        "yDomain": [round(float(min(y_values)), 6), round(float(max(y_values)), 6)],
    }
