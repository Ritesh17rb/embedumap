"""CLI entry point for embedumap."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.traceback import install

from .core import (
    BuildConfig,
    DEFAULT_DIMENSIONS,
    DEFAULT_MODEL,
    analyze_records,
    build_payload,
    dry_run_report,
    load_csv_source,
    prepare_rows,
    split_option_values,
)
from .html import render_html

install(show_locals=True)
load_dotenv(override=True)

HELP = """Build a standalone HTML UMAP visualization from a CSV using Gemini embeddings."""
app = typer.Typer(add_completion=False, help=HELP)


def normalize_popup_style(value: str) -> str:
    """Validate the popup style eagerly for cleaner CLI errors."""

    style = value.strip().lower()
    if style not in {"table", "grid", "list"}:
        raise typer.BadParameter("Popup style must be one of: table, grid, list")
    return style


@app.command()
def run(
    csv_input: str = typer.Argument(..., help="Local CSV path or HTTP(S) URL."),
    embedding_columns_raw: list[str] = typer.Option([], "--embedding-columns", help="Text columns to embed."),
    image_columns_raw: list[str] = typer.Option([], "--image-columns", help="Image URL/path columns to embed."),
    color_columns_raw: list[str] = typer.Option([], "--color-columns", help="Columns available for point colors."),
    filter_columns_raw: list[str] = typer.Option([], "--filter-columns", help="Columns exposed as filters."),
    timeline_column: str | None = typer.Option(None, "--timeline-column", help="Timeline column."),
    cluster_columns_raw: list[str] = typer.Option(
        ["embeddings"],
        "--cluster-columns",
        help='Cluster dimensions. Use "embeddings" for K-means on embeddings.',
    ),
    label_columns_raw: list[str] = typer.Option(
        [],
        "--label-column",
        "--label-columns",
        help="Columns used to build the primary hover label.",
    ),
    popup_style: str = typer.Option("table", "--popup-style", help="Popup layout: table, grid, or list."),
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="Gemini embedding model."),
    dimensions: int = typer.Option(DEFAULT_DIMENSIONS, "--dimensions", min=128, help="Embedding dimensionality."),
    sample: int | None = typer.Option(None, "--sample", min=1, help="Sample N rows before building."),
    output_path: Path = typer.Option(Path("index.html"), "--output", help="Where to write the HTML output."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs without embedding or writing HTML."),
) -> None:
    """Build the map or validate the plan for it."""

    popup_style = normalize_popup_style(popup_style)
    config = BuildConfig(
        csv_input=csv_input,
        output_path=output_path.expanduser().resolve(),
        embedding_columns=split_option_values(embedding_columns_raw),
        image_columns=split_option_values(image_columns_raw),
        color_columns=split_option_values(color_columns_raw),
        filter_columns=split_option_values(filter_columns_raw),
        cluster_columns=split_option_values(cluster_columns_raw) or ["embeddings"],
        label_columns=split_option_values(label_columns_raw),
        timeline_column=timeline_column.strip() if timeline_column else None,
        popup_style=popup_style,
        model=model.strip(),
        dimensions=dimensions,
        sample=sample,
        dry_run=dry_run,
    )
    if not config.embedding_columns and not config.image_columns:
        raise typer.BadParameter("At least one of --embedding-columns or --image-columns is required.")

    source = load_csv_source(config.csv_input)
    records, report = prepare_rows(source, config)
    if not records:
        raise typer.BadParameter("No usable rows remain after validation.")
    if config.dry_run:
        dry_run_report(source, config, records, report)
        return

    coords, cluster_ids, cluster_labels = analyze_records(records, config)
    payload = build_payload(source, config, records, coords, cluster_ids, cluster_labels)
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_path.write_text(render_html(payload), encoding="utf-8")
    typer.echo(f"Wrote {config.output_path}")


def main() -> None:
    """Console-script entry point."""

    app()


if __name__ == "__main__":
    main()
