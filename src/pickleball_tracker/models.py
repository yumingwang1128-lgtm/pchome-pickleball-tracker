from dataclasses import dataclass


@dataclass(frozen=True)
class ProductSnapshot:
    product_id: str
    name: str
    url: str
    query: str
    current_price: int
    original_price: int | None
    currency: str
    availability: str | None
    brand: str | None
    rating: float | None
    review_count: int | None
