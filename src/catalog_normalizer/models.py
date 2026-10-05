from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

RequiredString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]

NonNegativeInventory = Annotated[
    int,
    Field(ge=0),
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
    inventory: NonNegativeInventory | None = None
    status: str | None = None
