"""Entry point for the Odoo MCP server."""

import os
from dotenv import load_dotenv

load_dotenv()

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "8010"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
