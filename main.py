from fastapi import FastAPI

app = FastAPI(title="Marty Health Check Service", version="0.1.0")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["[::]:8000"]  # Dual stack IPv4/IPv6 binding
    config.use_reloader = True

    import asyncio

    asyncio.run(hypercorn.asyncio.serve(app, config))
