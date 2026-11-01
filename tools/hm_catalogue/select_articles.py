"""Select diverse H&M articles and download their corresponding Kaggle images."""

from __future__ import annotations

import argparse
import os
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

import pandas as pd
from PIL import Image, UnidentifiedImageError
from requests.exceptions import HTTPError

DEFAULT_INPUT = Path.home() / "Downloads" / "articles.csv"
DEFAULT_OUTPUT = Path.home() / "Downloads" / "selected_articles.csv"
DEFAULT_IMAGE_ROOT = Path.home() / "Downloads" / "hm_catalogue"
DEFAULT_KAGGLE_CONFIG_DIR = Path.home() / "Downloads"
DEFAULT_COMPETITION = "h-and-m-personalized-fashion-recommendations"
PROGRESS_INTERVAL = 100
OUTPUT_COLUMNS = [
    "article_id",
    "prod_name",
    "product_type_name",
    "colour_group_name",
    "image_path",
]
SOURCE_COLUMNS = OUTPUT_COLUMNS[:-1]


class KaggleImageSource:
    """List and download individual image files from a Kaggle competition/dataset."""

    def __init__(self, *, competition: str | None, dataset: str | None) -> None:
        if (competition is None) == (dataset is None):
            raise ValueError("Provide exactly one Kaggle competition or dataset.")
        kaggle_config = DEFAULT_KAGGLE_CONFIG_DIR / "kaggle.json"
        if not kaggle_config.is_file():
            raise FileNotFoundError(f"Kaggle credentials not found at {kaggle_config}")

        os.environ["KAGGLE_CONFIG_DIR"] = str(DEFAULT_KAGGLE_CONFIG_DIR)

        from kaggle.api.kaggle_api_extended import KaggleApi

        self.api = KaggleApi()
        self.api.authenticate()
        self.competition = competition
        self.dataset = dataset

    def download(self, remote_path: str, destination: Path) -> None:
        """Download one image and handle Kaggle's per-file ZIP wrapper."""
        download_dir = destination.parent
        filename = PurePosixPath(remote_path).name
        downloaded = download_dir / filename
        zipped = download_dir / f"{filename}.zip"

        if not downloaded.is_file() and not zipped.is_file():
            if self.competition:
                self.api.competition_download_file(
                    self.competition,
                    file_name=remote_path,
                    path=str(download_dir),
                    force=True,
                    quiet=True,
                )
            else:
                assert self.dataset is not None
                self.api.dataset_download_file(
                    self.dataset,
                    file_name=remote_path,
                    path=str(download_dir),
                    force=True,
                    quiet=True,
                )

        if downloaded.is_file():
            if downloaded != destination:
                shutil.move(downloaded, destination)
            return

        if not zipped.is_file():
            raise RuntimeError(
                f"Kaggle reported success but neither the image nor its ZIP "
                f"was found in {download_dir}"
            )

        with zipfile.ZipFile(zipped) as archive:
            matches = [
                member
                for member in archive.infolist()
                if PurePosixPath(member.filename).name == filename
                and not member.is_dir()
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"Expected one {filename} image in {zipped}, found {len(matches)}"
                )
            with archive.open(matches[0]) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)

        zipped.unlink()


def image_relative_path(article_id: str) -> str:
    """Build the Kaggle image path from a zero-padded article ID."""
    return f"images/{article_id[:3]}/{article_id}.jpg"


def is_valid_jpeg(path: Path) -> bool:
    """Check that the file is a readable JPEG; visual quality needs human review."""
    try:
        with Image.open(path) as image:
            if image.format != "JPEG":
                return False
            image.verify()
    except (OSError, UnidentifiedImageError):
        return False
    return True


def save_selection(rows: list[dict[str, Any]], output_path: Path) -> None:
    """Atomically save selected rows so progress survives interruption."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.name}.tmp")
    pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(temporary_path, index=False)
    temporary_path.replace(output_path)


def select_and_download(
    input_path: Path,
    output_path: Path,
    image_root: Path,
    count: int,
    seed: int,
    image_source: KaggleImageSource,
) -> pd.DataFrame:
    """Select a varied sample, retaining only articles with valid downloaded JPEGs."""
    articles = pd.read_csv(input_path, dtype={"article_id": "string"})
    missing_columns = sorted(set(SOURCE_COLUMNS) - set(articles.columns))
    if missing_columns:
        raise ValueError(
            f"CSV is missing required columns: {', '.join(missing_columns)}"
        )

    candidates = articles[SOURCE_COLUMNS].copy()
    for column in SOURCE_COLUMNS:
        candidates[column] = candidates[column].astype("string").str.strip()

    candidates = candidates.dropna(subset=SOURCE_COLUMNS)
    for column in SOURCE_COLUMNS:
        candidates = candidates[candidates[column].ne("")]
    candidates = candidates[
        candidates["article_id"].str.fullmatch(r"\d{10}", na=False)
    ].drop_duplicates(subset="article_id")

    shuffled = candidates.sample(frac=1, random_state=seed).reset_index(drop=True)
    shuffled["_shuffle_order"] = range(len(shuffled))
    shuffled["_bucket_round"] = shuffled.groupby(
        ["product_type_name", "colour_group_name"], sort=True
    ).cumcount()
    shuffled = shuffled.sort_values(["_bucket_round", "_shuffle_order"], kind="stable")

    selected_rows: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    image_root.mkdir(parents=True, exist_ok=True)

    for row in shuffled.itertuples(index=False):
        article_id = str(row.article_id)
        relative_path = image_relative_path(article_id)
        local_path = image_root / relative_path
        if local_path.is_file() and is_valid_jpeg(local_path):
            selected_rows.append(
                {
                    "article_id": article_id,
                    "prod_name": row.prod_name,
                    "product_type_name": row.product_type_name,
                    "colour_group_name": row.colour_group_name,
                    "image_path": relative_path,
                }
            )
            selected_ids.add(article_id)
            if len(selected_rows) == count:
                break

    save_selection(selected_rows, output_path)
    if selected_rows:
        print(f"Found {len(selected_rows):,} valid cached images.")

    for row in shuffled.itertuples(index=False):
        if len(selected_rows) == count:
            break
        article_id = str(row.article_id)
        if article_id in selected_ids:
            continue

        relative_path = image_relative_path(article_id)
        local_path = image_root / relative_path
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if local_path.exists():
            local_path.unlink()
        try:
            image_source.download(relative_path, local_path)
        except HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if status_code == 404:
                continue
            if status_code == 429:
                save_selection(selected_rows, output_path)
                raise RuntimeError(
                    f"Kaggle rate-limited image downloads after "
                    f"{len(selected_rows):,} valid articles. A checkpoint was "
                    f"saved to {output_path}. Stop this run and retry later; "
                    "valid images are retained and will be reused."
                ) from exc
            raise
        if not is_valid_jpeg(local_path):
            local_path.unlink(missing_ok=True)
            continue

        selected_rows.append(
            {
                "article_id": article_id,
                "prod_name": row.prod_name,
                "product_type_name": row.product_type_name,
                "colour_group_name": row.colour_group_name,
                "image_path": relative_path,
            }
        )
        selected_ids.add(article_id)
        if len(selected_rows) % PROGRESS_INTERVAL == 0:
            save_selection(selected_rows, output_path)
            print(f"Selected and verified {len(selected_rows):,}/{count:,} articles.")
        if len(selected_rows) == count:
            break

    if len(selected_rows) < count:
        raise RuntimeError(
            f"Found and downloaded only {len(selected_rows):,} valid images for "
            f"{count:,} requested articles. Check the Kaggle file listing and "
            "whether its image files are individually downloadable."
        )

    selected = pd.DataFrame(selected_rows, columns=OUTPUT_COLUMNS)
    save_selection(selected_rows, output_path)
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Select diverse H&M articles with valid downloaded Kaggle photos."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Source CSV (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Selected CSV destination (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--image-root",
        type=Path,
        default=DEFAULT_IMAGE_ROOT,
        help=f"Directory for downloaded images (default: {DEFAULT_IMAGE_ROOT})",
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--competition",
        help=f"Kaggle competition slug (default: {DEFAULT_COMPETITION})",
    )
    source_group.add_argument(
        "--dataset",
        help="Kaggle dataset slug, in owner/dataset-name format",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=2000,
        help="Number of valid images/articles to select (default: 2000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for repeatable selection (default: 42)",
    )
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be a positive integer")
    if not args.input.is_file():
        parser.error(f"Input CSV does not exist: {args.input}")

    try:
        image_source = KaggleImageSource(
            competition=args.competition
            or (None if args.dataset else DEFAULT_COMPETITION),
            dataset=args.dataset,
        )
        selected = select_and_download(
            args.input,
            args.output,
            args.image_root,
            args.count,
            args.seed,
            image_source,
        )
    except KeyboardInterrupt:
        parser.exit(
            130,
            "\nInterrupted; downloaded images and the latest checkpoint are kept.\n",
        )

    print(f"Saved {len(selected):,} articles to {args.output}")
    print(f"Downloaded images are under {args.image_root}")
    print(
        f"Covered {selected['product_type_name'].nunique()} product types and "
        f"{selected['colour_group_name'].nunique()} colours."
    )
    print("\nMost represented product types:")
    print(selected["product_type_name"].value_counts().head(10).to_string())
    print("\nMost represented colours:")
    print(selected["colour_group_name"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
