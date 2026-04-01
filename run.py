#!/usr/bin/env python3
import uvicorn

from backend.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        ws="wsproto",
    )
