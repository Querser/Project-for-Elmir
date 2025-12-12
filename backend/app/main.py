from fastapi import FastAPI

app = FastAPI(title="Volleyball School API")


@app.get("/health", tags=["service"])
def health_check():
    """
    Простой health-check эндпоинт, чтобы проверить,
    что backend запущен и отвечает.
    """
    return {"status": "ok"}
