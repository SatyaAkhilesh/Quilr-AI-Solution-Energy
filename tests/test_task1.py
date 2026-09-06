import pytest
from pydantic import TypeAdapter, ValidationError

from task1_mcp_server.server import (
    CustomerId,
    PositiveAmount,
    RefundReason,
)


def test_valid_customer_id():
    adapter = TypeAdapter(CustomerId)
    assert adapter.validate_python("CUST-12345") == "CUST-12345"


@pytest.mark.parametrize(
    "value",
    [
        "12345",
        "CUST-1234",
        "CUST-123456",
        "CUST-ABCDE",
        "cust-12345",
    ],
)
def test_invalid_customer_id(value):
    adapter = TypeAdapter(CustomerId)

    with pytest.raises(ValidationError):
        adapter.validate_python(value)


def test_positive_amount():
    adapter = TypeAdapter(PositiveAmount)
    assert adapter.validate_python(25.5) == 25.5


@pytest.mark.parametrize("value", [0, -1, -50])
def test_invalid_amount(value):
    adapter = TypeAdapter(PositiveAmount)

    with pytest.raises(ValidationError):
        adapter.validate_python(value)


def test_valid_refund_reason():
    adapter = TypeAdapter(RefundReason)
    reason = "Customer requested refund"

    assert adapter.validate_python(reason) == reason


def test_short_refund_reason():
    adapter = TypeAdapter(RefundReason)

    with pytest.raises(ValidationError):
        adapter.validate_python("refund")