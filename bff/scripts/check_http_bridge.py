import asyncio
import json
import os
import httpx


async def main():
    base = os.getenv("BFF_HTTP_URL", "http://127.0.0.1:8002").rstrip("/")
    username = os.environ["BFF_USERNAME"]
    password = os.environ["BFF_PASSWORD"]
    async with httpx.AsyncClient(timeout=40) as client:
        login = await client.post(
            base + "/auth/login",
            json={"username": username, "password": password},
        )
        print(f"POST /auth/login: HTTP {login.status_code}")
        if login.status_code != 200:
            raise SystemExit("Failed on /auth/login")
        for route in ("/healthz", "/projects", "/projects/mine", "/hardware"):
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
