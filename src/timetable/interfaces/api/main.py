from fastapi import FastAPI

app = FastAPI(
    title="Timetable Solver API",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "healthy"}
