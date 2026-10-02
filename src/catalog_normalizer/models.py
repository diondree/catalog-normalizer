from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: str
    name: str
    description: str | None = None
    brand: str | None = None
    category: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    inventory: int | None = None
    status: str | None = None