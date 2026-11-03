import asyncio
import json
import os
import httpx


async def main():
    base = os.getenv("BFF_HTTP_URL", "http://127.0.0.1:8002").rstrip("/")
    async with httpx.AsyncClient(timeout=40) as client:
        for route in ("/healthz", "/projects", "/hardware"):
            response = await client.get(base + route)
            print(f"GET {route}: HTTP {response.status_code}")
            try:
                print(json.dumps(response.json(), indent=2)[:2500])
            except ValueError:
                print(response.text[:500])
            if response.status_code != 200:
                raise SystemExit(f"Failed on {route}")
    print("SUCCESS: HTTP -> gRPC -> REST -> Azure")


if __name__ == "__main__":
    asyncio.run(main())
