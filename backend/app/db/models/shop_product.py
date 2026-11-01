from sqlalchemy import DECIMAL, JSON, TEXT, Boolean, ForeignKey, String, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ShopProduct(Base):
    __tablename__ = "shop_products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    shop_id: Mapped[str] = mapped_column(ForeignKey("shops.id"), nullable=False)
    external_product_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    color: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    embedding: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_s3_url: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    product_url: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    price: Mapped[float | None] = mapped_column(DECIMAL(10, 2), nullable=True)
    is_example: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
