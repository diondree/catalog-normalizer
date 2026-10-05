from decimal import Decimal

from pydantic import BaseModel, ConfigDict, StringConstraints

from typing import Annotated

RequiredString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]
class ProductSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sku: RequiredString
    name: RequiredString
    description: str | None = None
    brand: str | None = None
    category: str | None = None
    price: Decimal | None = None
    currency: str | None = None
    inventory: int | None = None
    status: str | None = None