import asyncio
from mcp import Client
from bs4 import BeautifulSoup

async def main() -> None:
    async with Client("http://localhost:8000/mcp") as client:
        steps = [
            # ("open", {"url": "https://search.brave.com/"}),
            # ("wait", {"selector": "#searchbox", "timeout": 15.0}),
            # ("fill", {"selector": "#searchbox", "text": "ob havo", "clear": True}),
            # ("submit", {"selector": "#searchform", "navigates": True}),
            ("open", {"url": "https://search.brave.com/search?q=ob+havo+andijon"}),
            ("wait", {"selector": "button.button", "timeout": 15.0}),
            ("click", {"selector": "button.button"}),
            ("wait", {"selector": "section[id='mixed-main']", "timeout": 15.0}),
            ("html", {"selector": "section[id='mixed-main']"}),
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
            html = last_result.structured_content.get("result")
            soup = BeautifulSoup(html, "html.parser")

            links = list(dict.fromkeys(
                a["href"]
                for a in soup.select("div.result-content a[href]")
            ))
            print(links)

asyncio.run(main())