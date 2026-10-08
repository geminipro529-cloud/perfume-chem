"""Reference data endpoints"""

from pathlib import PurePosixPath, PureWindowsPath
from typing import List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.data_loader import DataLoader

router = APIRouter(
    prefix="/api/v1/reference",
    tags=["reference_data"]
)


class CompoundResponse(BaseModel):
    name: str
    cas: str
    category: str
    scent: List[str]
    note: str
    volatility: str
    molecular_weight: float
    ifra_limit: float
    allergen: bool


class FragranceFamilyResponse(BaseModel):
    name: str
    description: str
    key_materials: List[str]
    typical_uses: List[str]


class StatisticsResponse(BaseModel):
    total_compounds: int
    total_fragrance_families: int
    concentration_types: int


@router.get("/compounds", response_model=dict)
async def list_compounds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500)
):
    """Get all chemical compounds"""
    all_compounds = DataLoader.list_all_compounds()
    return {
        "total": len(all_compounds),
        "compounds": all_compounds[skip:skip + limit]
    }


@router.get("/compounds/search", response_model=dict)
async def search_compounds(q: str = Query(..., min_length=2)):
    """Search compounds by name or scent"""
    results = DataLoader.search_compounds(q)
    return {
        "query": q,
        "count": len(results),
        "results": results
    }


@router.get("/compounds/{cas_number}")
async def get_compound_by_cas(cas_number: str):
    """Get compound by CAS number"""
    compound = DataLoader.get_compound_by_cas(cas_number)
    if not compound:
        raise HTTPException(status_code=404, detail=f"Compound with CAS {cas_number} not found")
    return compound


@router.get("/compounds/name/{name}")
async def get_compound_by_name(name: str):
    """Get compound by name"""
    compound = DataLoader.get_compound_by_name(name)
    if not compound:
        raise HTTPException(status_code=404, detail=f"Compound '{name}' not found")
    return compound


@router.get("/families")
async def list_fragrance_families():
    """Get all fragrance families"""
    families = DataLoader.load_fragrance_families()
    return {
        "total": len(families.get("fragrance_families", [])),
        "families": families.get("fragrance_families", [])
    }


@router.get("/families/{family_name}")
async def get_fragrance_family(family_name: str):
    """Get specific fragrance family"""
    family = DataLoader.get_fragrance_family(family_name)
    if not family:
        raise HTTPException(status_code=404, detail=f"Family '{family_name}' not found")
    return family


@router.get("/concentration-types")
async def list_concentration_types():
    """Get all concentration types (EDP, EDT, etc.)"""
    families = DataLoader.load_fragrance_families()
    return {
        "total": len(families.get("concentration_types", [])),
        "types": families.get("concentration_types", [])
    }


@router.get("/statistics")
async def get_statistics():
    """Get data statistics and file locations"""
    return DataLoader.get_statistics()


@router.get("/health")
async def data_health():
    """Check if all reference data is loaded"""
    stats = DataLoader.get_statistics()
    return {
        "status": "healthy" if stats["total_compounds"] > 0 else "unhealthy",
        "compounds_loaded": stats["total_compounds"],
        "families_loaded": stats["total_fragrance_families"],
        "knowledge_documents": stats["knowledge_documents"]
    }


@router.get("/knowledge")
async def list_knowledge_files():
    """Get list of all knowledge base documents"""
    files = DataLoader.list_knowledge_files()
    return {
        "total": len(files),
        "files": files
    }


@router.get("/knowledge/{filepath:path}")
async def get_knowledge_file(filepath: str):
    """Get content of a knowledge file"""
    content = DataLoader.load_knowledge_file(filepath)
    if not content:
        # Echo only a relative request; never an absolute path.
        if PurePosixPath(filepath).anchor or PureWindowsPath(filepath).anchor:
            raise HTTPException(status_code=404, detail="Knowledge file not found")
        raise HTTPException(status_code=404, detail=f"Knowledge file '{filepath}' not found")
    return {
        "filename": filepath,
        "content": content
    }


@router.get("/knowledge/search/{query}")
async def search_knowledge(query: str):
    """Search through knowledge base"""
    results = DataLoader.search_knowledge(query)
    return {
        "query": query,
        "files_with_matches": len(results["files"]),
        "total_matches": len(results["matches"]),
        "files": results["files"],
        "matches": results["matches"]
    }
