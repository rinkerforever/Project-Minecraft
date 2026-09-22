from minecraft_manager.app import app
from minecraft_manager.config import settings

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
