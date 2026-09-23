"""One source for the existing web credit packs; payment product IDs stay unchanged."""
from decimal import Decimal

CREDIT_PACKS = (
    {"amount": 10, "price": Decimal("1.99"), "name": "Starter Pack"},
    {"amount": 50, "price": Decimal("6.99"), "name": "Active Dater"},
    {"amount": 200, "price": Decimal("19.99"), "name": "Power User"},
)

STARTER_PACK = CREDIT_PACKS[0]
