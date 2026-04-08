from fastapi import APIRouter
from pydantic import BaseModel

from core.project_store import save_project, load_project, list_projects, delete_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


class SaveRequest(BaseModel):
    state: dict
    name: str = ""


@router.post("/save")
async def save(req: SaveRequest):
    project_id = save_project(req.state, req.name)
    return {"project_id": project_id}


@router.get("/list")
async def list_all():
    return {"projects": list_projects()}


@router.get("/load/{project_id:path}")
async def load(project_id: str):
    state = load_project(project_id)
    return {"state": state}


@router.delete("/{project_id:path}")
async def delete(project_id: str):
    delete_project(project_id)
    return {"ok": True}
