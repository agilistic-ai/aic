import os

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from .booking_loop import Slot

from .booking_store import BookingStore


server = FastMCP("Workshop availability")
store = BookingStore(os.environ["AIC_BOOKING_DB"], members=set())


class Availability(BaseModel):
    slots: list[Slot]


@server.tool()
def list_slots(day: str) -> Availability:
    """Return available assessment slots for one UTC calendar date."""
    return Availability(slots=store.list_slots(day))


if __name__ == "__main__":
    server.run(transport="stdio")
