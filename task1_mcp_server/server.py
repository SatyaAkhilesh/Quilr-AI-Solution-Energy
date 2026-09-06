import logging
import sys
from typing import Annotated
from mcp.server.mcpserver import MCPServer

from pydantic import Field


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)

mcp = MCPServer("customer-service")


CUSTOMERS = {
    "CUST-12345": {
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "status": "active",
    },
    "CUST-67890": {
        "name": "Bob Smith",
        "email": "bob@example.com",
        "status": "active",
    },
}


CustomerId = Annotated[
    str,
    Field(
        pattern=r"^CUST-\d{5}$",
        description="Customer ID in the format CUST-XXXXX",
    ),
]

PositiveAmount = Annotated[
    float,
    Field(gt=0),
]

RefundReason = Annotated[
    str,
    Field(min_length=10),
]


@mcp.tool()
def get_customer_record(customer_id: CustomerId) -> dict:
    logger.info("Looking up customer %s", customer_id)

    customer = CUSTOMERS.get(customer_id)

    if not customer:
        return {
            "found": False,
            "customer_id": customer_id,
        }

    return {
        "found": True,
        "customer_id": customer_id,
        "record": customer,
    }


@mcp.tool()
def trigger_refund(
    customer_id: CustomerId,
    amount: PositiveAmount,
    reason: RefundReason,
) -> dict:
    logger.info(
        "Refund request for %s, amount %.2f",
        customer_id,
        amount,
    )

    if customer_id not in CUSTOMERS:
        return {
            "success": False,
            "error": "customer_not_found",
        }

    return {
        "success": True,
        "refund_id": f"REF-{customer_id[-5:]}",
        "customer_id": customer_id,
        "amount": amount,
        "reason": reason,
        "status": "submitted",
    }


if __name__ == "__main__":
    logger.info("Starting customer MCP server")
    mcp.run()