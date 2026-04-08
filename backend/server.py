from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import projects, sources, structure, topics, visuals

app = FastAPI(title="Media Tool API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(topics.router)
app.include_router(sources.router)
app.include_router(structure.router)
app.include_router(visuals.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
