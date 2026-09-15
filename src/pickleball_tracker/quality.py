from dataclasses import dataclass

from .models import ProductSnapshot


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_snapshot(snapshot: ProductSnapshot) -> ValidationResult:
    errors: list[str] = []
    if not snapshot.product_id:
        errors.append("product_id is required")
    if not snapshot.name:
        errors.append("name is required")
    if snapshot.current_price < 0:
        errors.append("current_price must be non-negative")
    if snapshot.original_price is not None and snapshot.original_price < snapshot.current_price:
        errors.append("original_price must be greater than or equal to current_price")
    if snapshot.rating is not None and not 0 <= snapshot.rating <= 5:
        errors.append("rating must be between 0 and 5")
    if snapshot.review_count is not None and snapshot.review_count < 0:
        errors.append("review_count must be non-negative")
    return ValidationResult(tuple(errors))
