from fastapi import FastAPI

from app.shared.error_handlers import register_error_handlers

app = FastAPI(title="Transaction Ledger API", version="1.0.0")
register_error_handlers(app)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
