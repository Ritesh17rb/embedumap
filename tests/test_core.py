"""Fast unit tests for embedumap core helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from embedumap.core import (
    BuildConfig,
    CsvSource,
    build_payload,
    default_cache_path,
    direct_cluster_labels,
    split_option_values,
)


def test_split_option_values_flattens_and_deduplicates() -> None:
    values = split_option_values(["text1,text2", "text2", " text3 ", ""])
    assert values == ["text1", "text2", "text3"]


def test_direct_cluster_labels_use_raw_column_values() -> None:
    class Record:
        def __init__(self, value: str) -> None:
            self.raw = {"theme": value}

    labels, label_map = direct_cluster_labels([Record("a"), Record("b"), Record("a")], ["theme"])
    assert labels.tolist() == [0, 1, 0]
    assert label_map == {0: "a", 1: "b"}


def test_build_payload_includes_popup_sort_columns() -> None:
    source = CsvSource(
        label="sample.csv",
        frame=pd.DataFrame(columns=["title", "year"]),
        csv_path=None,
        csv_url=None,
    )
    config = BuildConfig(
        csv_input="sample.csv",
        output_path=Path("index.html"),
        embedding_columns=["title"],
        image_columns=[],
        audio_columns=[],
        audio_metadata_columns=[],
        color_columns=["year"],
        filter_columns=[],
        cluster_columns=["embeddings"],
        label_columns=[],
        timeline_column="year",
        popup_style="table",
        model="model",
        cluster_naming_model="gemini-3-flash-preview",
        cluster_names=False,
        dimensions=768,
        sample=None,
        dry_run=False,
    )

    class Record:
        row_index = 0
        raw = {"title": "Hello", "year": "2024"}
        tooltip = raw
        label = "Hello"
        audio_metadata_text = ""
        timeline_text = "2024-01-01 00:00:00 UTC"
        timeline_ms = 1704067200000
        images = []
        audios = []

    payload = build_payload(source, config, [Record()], np.array([[0.0, 0.0]]), np.array([0]), {0: "Cluster 1"})
    assert payload["defaultSort"] == "year"
    assert payload["sortColumns"] == ["_row_index", "year", "title"]
    assert payload["audioColumns"] == []


def test_default_cache_path_tracks_output_directory() -> None:
    output_path = Path("/tmp/embedumap/output/index.html")
    assert default_cache_path(output_path) == Path("/tmp/embedumap/output/embedumap.duckdb")
