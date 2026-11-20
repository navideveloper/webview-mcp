# Browser & MCP Server

A Python library to control a shared web browser either directly via script or remotely using a Model Context Protocol (MCP) server.

## Quickstart: Direct Usage

Use the browser directly in Python:

```python
from browser import Browser, run

def main(browser: Browser) -> None:
    page = browser.open("https://jadval.adu.uz")
    print("Title:", page.title)
    print("Content:", browser.text)

if __name__ == "__main__":
    run(main)
```

## Running the Server

Start the MCP server over HTTP:

```bash
python mcp-server.py --host 127.0.0.1 --port 8000
```

### CLI Arguments

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--show` | `bool` | `False` | Display the browser UI window |
| `--session` | `bool` | `False` | Save cookies and session state |
| `--host` | `str` | `127.0.0.1` | HTTP server host address |
| `--port` | `int` | `8000` | HTTP server port number |

## Available MCP Tools

* **Navigation**: `open`, `page`, `back`, `forward`, `reload`, `scroll_down`, `wait`
* **Extraction**: `content`, `links`, `extract`, `attribute`, `html`
* **Interaction**: `click`, `fill`, `submit`

## Client Example

Control the server programmatically using the MCP client:

```python
import asyncio
from mcp import Client

async def main() -> None:
    async with Client("http://localhost:8000/mcp") as client:
        # Navigate and wait for form
        await client.call_tool("open", {"url": "https://adekvatserver.ru/stats?server=4"})
        await client.call_tool("wait", {"selector": "#search_stats", "timeout": 15.0})
        
        # Fill search input and click submit
        await client.call_tool("fill", {"selector": "#search_stats", "text": "salokhiddinov", "clear": True})
        await client.call_tool("click", {"selector": "button[type='submit']", "navigates": False})
        
        # Wait for results table and extract text
        await client.call_tool("wait", {"selector": "table", "timeout": 15.0})
        result = await client.call_tool("extract", {"selector": "table"})
        
        print("Scraped Data:", result.content)

asyncio.run(main())
```