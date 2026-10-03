"""Landing page (serves index.html at /)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from config import ROOT

router = APIRouter(tags=["pages"])


@router.get("/")
def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@router.get("/upload")
def upload_page() -> FileResponse:
    return FileResponse(ROOT / "upload.html")
