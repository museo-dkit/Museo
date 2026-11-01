"""Import the reviewed H&M sample into the Modu shop_products table."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

BACKEND_PATH = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from app.db.models.shop import Shop
from app.db.models.shop_product import ShopProduct
from app.db.session import SessionLocal

DEFAULT_INPUT = Path.home() / "Downloads" / "selected_articles.csv"
DEFAULT_IMAGE_ROOT = Path.home() / "Downloads" / "hm_catalogue"
EXAMPLE_SHOP_NAME = "H&M Kaggle Examples"
IMAGE_KEY_PREFIX = "hm/articles"
REQUIRED_COLUMNS = {
    "article_id",
    "prod_name",
    "product_type_name",
    "colour_group_name",
    "image_path",
}


@dataclass(frozen=True)
class CatalogueRow:
    article_id: str
    name: str
    category: str
    color: str
    image_key: str


def load_rows(input_path: Path, image_root: Path) -> list[CatalogueRow]:
    """Validate CSV rows and local images before opening a database session."""
    rows: list[CatalogueRow] = []
    seen_ids: set[str] = set()
    resolved_image_root = image_root.resolve()

    with input_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                f"CSV is missing required columns: {', '.join(sorted(missing_columns))}"
            )

        for line_number, record in enumerate(reader, start=2):
            article_id = (record["article_id"] or "").strip()
            name = (record["prod_name"] or "").strip()
            category = (record["product_type_name"] or "").strip()
            color = (record["colour_group_name"] or "").strip()
            image_path = (record["image_path"] or "").strip()

            if not re.fullmatch(r"\d{10}", article_id):
                raise ValueError(
                    f"Invalid 10-digit article_id on CSV line {line_number}"
                )
            if article_id in seen_ids:
                raise ValueError(f"Duplicate article_id {article_id} in CSV")
            if not name or not category or not color:
                raise ValueError(f"Missing product metadata on CSV line {line_number}")
            if len(name) > 200 or len(category) > 80 or len(color) > 80:
                raise ValueError(
                    f"Product metadata exceeds the database column size on "
                    f"CSV line {line_number}"
                )

            expected_path = Path("images") / article_id[:3] / f"{article_id}.jpg"
            if Path(image_path) != expected_path:
                raise ValueError(
                    f"Unexpected image_path on CSV line {line_number}: "
                    f"expected {expected_path.as_posix()}"
                )

            local_image = (resolved_image_root / expected_path).resolve()
            if not local_image.is_relative_to(resolved_image_root):
                raise ValueError(f"Image path escapes image root on line {line_number}")
            if not local_image.is_file() or local_image.stat().st_size == 0:
                raise FileNotFoundError(
                    f"Image is missing or empty for article {article_id}: {local_image}"
                )

            rows.append(
                CatalogueRow(
                    article_id=article_id,
                    name=name,
                    category=category,
                    color=color,
                    image_key=f"{IMAGE_KEY_PREFIX}/{expected_path.as_posix()}",
                )
            )
            seen_ids.add(article_id)

    if not rows:
        raise ValueError(f"No product rows found in {input_path}")
    return rows


def import_rows(rows: list[CatalogueRow]) -> tuple[int, int]:
    """Idempotently create or update example products in a dedicated shop."""
    created_count = 0
    updated_count = 0

    with SessionLocal.begin() as session:
        shops = session.scalars(
            select(Shop).where(Shop.name == EXAMPLE_SHOP_NAME)
        ).all()
        if len(shops) > 1:
            raise RuntimeError(
                f"More than one shop named {EXAMPLE_SHOP_NAME!r} exists; "
                "resolve the duplicate shops before importing."
            )

        shop = shops[0] if shops else Shop(id=str(uuid4()), name=EXAMPLE_SHOP_NAME)
        if not shops:
            session.add(shop)
            session.flush()

        existing_products = {
            product.external_product_id: product
            for product in session.scalars(
                select(ShopProduct).where(
                    ShopProduct.shop_id == shop.id,
                    ShopProduct.external_product_id.in_(
                        [row.article_id for row in rows]
                    ),
                )
            )
        }

        for row in rows:
            product = existing_products.get(row.article_id)
            if product is None:
                product = ShopProduct(
                    id=str(uuid4()),
                    shop_id=shop.id,
                    external_product_id=row.article_id,
                )
                session.add(product)
                created_count += 1
            else:
                updated_count += 1

            product.name = row.name
            product.category = row.category
            product.color = row.color
            product.price = None
            product.image_s3_url = row.image_key
            product.is_example = True

    return created_count, updated_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import selected H&M sample products into shop_products."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--image-root", type=Path, default=DEFAULT_IMAGE_ROOT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the CSV and image files without connecting to MySQL.",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"Input CSV does not exist: {args.input}")
    if not args.image_root.is_dir():
        parser.error(f"Image directory does not exist: {args.image_root}")

    rows = load_rows(args.input, args.image_root)
    print(f"Validated {len(rows):,} products and their local image files.")

    if args.dry_run:
        print(
            f"Dry run only. Would import into {EXAMPLE_SHOP_NAME!r} with "
            "price=NULL, is_example=true, and image keys under "
            f"{IMAGE_KEY_PREFIX}/."
        )
        return

    created_count, updated_count = import_rows(rows)
    print(
        f"Import committed: {created_count:,} created, "
        f"{updated_count:,} updated in {EXAMPLE_SHOP_NAME!r}."
    )


if __name__ == "__main__":
    main()
