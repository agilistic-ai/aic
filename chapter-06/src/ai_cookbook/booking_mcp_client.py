import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .booking_loop import Slot


def reader(database):
    database = str(Path(database).resolve())

    async def call(day):
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "ai_cookbook.booking_mcp_server"],
            env={"AIC_BOOKING_DB": database},
        )
        async with asyncio.timeout(15):
            async with stdio_client(parameters) as (incoming, outgoing):
                async with ClientSession(incoming, outgoing) as session:
                    await session.initialize()
                    catalog = await session.list_tools()
                    matches = [tool for tool in catalog.tools if tool.name == "list_slots"]
                    if len(matches) != 1:
                        raise ValueError("Expected availability tool is missing.")
                    schema = matches[0].inputSchema
                    if (set(schema.get("properties", {})) != {"day"}
                            or schema["properties"]["day"].get("type") != "string"
                            or schema.get("required") != ["day"]):
                        raise ValueError("Availability tool contract changed.")
                    result = await session.call_tool("list_slots", {"day": day})
                    if result.isError or result.structuredContent is None:
                        raise ValueError("Availability lookup failed.")
                    payload = result.structuredContent
                    if len(json.dumps(payload).encode()) > 16_000:
                        raise ValueError("Availability response is too large.")
                    if set(payload) != {"slots"} or not isinstance(payload["slots"], list):
                        raise ValueError("Unexpected availability payload.")
                    if len(payload["slots"]) > 20:
                        raise ValueError("Too many availability records.")
                    return [Slot.model_validate(row).model_dump() for row in payload["slots"]]

    return lambda day: asyncio.run(call(day))
