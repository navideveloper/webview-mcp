import asyncio
from mcp import Client


async def main() -> None:
    async with Client("http://localhost:8000/mcp") as client:
        steps = [
            ("open", {"url": "https://adekvatserver.ru/stats?server=4"}),
            ("wait", {"selector": "#search_stats", "timeout": 15.0}),
            ("fill", {"selector": "#search_stats", "text": "salokhiddinov", "clear": True}),
            ("click", {"selector": "button[type='submit'].btn", "navigates": False}),
            ("wait", {"selector": "table", "timeout": 15.0}),
            ("extract", {"selector": "table"}),
        ]

        last_result = None
        for tool_name, args in steps:
            res = await client.call_tool(tool_name, args)
            print(f"[{tool_name}] is_error={res.is_error}")
            if res.is_error:
                print("Xato tafsiloti:", res.content)
                return
            last_result = res

        if last_result and last_result.structured_content:
            print(last_result.structured_content.get("result"))


asyncio.run(main())