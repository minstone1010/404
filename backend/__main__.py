from backend.config import settings
import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host=settings.host, port=settings.port, workers=1)
