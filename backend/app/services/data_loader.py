"""Data loading and caching utilities"""

import json
import logging
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Optional, TypedDict, cast

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
BACKEND_DATA_DIR = Path(__file__).parent.parent.parent / "data"
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent / "knowledge"

JsonObject = dict[str, Any]


class KnowledgeMatch(TypedDict):
    """A matching line returned by a knowledge-base search."""

    file: str
    line_number: int
    content: str


class KnowledgeSearchResult(TypedDict):
    """Structured result from a knowledge-base search."""

    files: list[str]
    matches: list[KnowledgeMatch]


def _is_unsafe_relative_name(name: str) -> bool:
    """True when a caller-supplied name is not a plain relative path."""
    for flavour in (PurePosixPath, PureWindowsPath):
        pure = flavour(name)
        if pure.anchor or pure.drive or ".." in pure.parts:
            return True
    return False


class DataLoader:
    """Load and cache reference data files"""

    @staticmethod
    @lru_cache(maxsize=1)
    def load_compounds() -> JsonObject:
        """Load chemical compounds database"""
        try:
            compounds_file = DATA_DIR / "compounds.json"
            if compounds_file.exists():
                with open(compounds_file, 'r') as f:
                    data = cast(JsonObject, json.load(f))
                logger.info(f"Loaded {len(data.get('compounds', []))} compounds")
                return data
        except Exception as e:
            logger.error(f"Failed to load compounds.json: {e}")
        return {"compounds": []}

    @staticmethod
    @lru_cache(maxsize=1)
    def load_fragrance_families() -> JsonObject:
        """Load fragrance classification data"""
        try:
            families_file = BACKEND_DATA_DIR / "reference" / "fragrance_reference.json"
            if families_file.exists():
                with open(families_file, 'r') as f:
                    data = cast(JsonObject, json.load(f))
                logger.info("Loaded fragrance reference data")
                return data
        except Exception as e:
            logger.error(f"Failed to load fragrance_reference.json: {e}")
        return {"fragrance_families": [], "concentration_types": []}

    @staticmethod
    def get_compound_by_cas(cas_number: str) -> Optional[JsonObject]:
        """Get a compound by CAS number"""
        compounds = DataLoader.load_compounds()
        for compound in cast(list[JsonObject], compounds.get("compounds", [])):
            if compound.get("cas") == cas_number:
                return compound
        return None

    @staticmethod
    def get_compound_by_name(name: str) -> Optional[JsonObject]:
        """Get a compound by name"""
        compounds = DataLoader.load_compounds()
        for compound in cast(list[JsonObject], compounds.get("compounds", [])):
            if cast(str, compound.get("name")).lower() == name.lower():
                return compound
        return None

    @staticmethod
    def search_compounds(query: str) -> list[JsonObject]:
        """Search compounds by name or scent"""
        compounds = DataLoader.load_compounds()
        results: list[JsonObject] = []
        query_lower = query.lower()

        for compound in cast(list[JsonObject], compounds.get("compounds", [])):
            # Search in name
            if query_lower in compound.get("name", "").lower():
                results.append(compound)
            # Search in scent profile
            elif any(query_lower in scent.lower() for scent in compound.get("scent", [])):
                results.append(compound)

        return results

    @staticmethod
    def get_fragrance_family(family_name: str) -> Optional[JsonObject]:
        """Get fragrance family details"""
        data = DataLoader.load_fragrance_families()
        for family in cast(list[JsonObject], data.get("fragrance_families", [])):
            if cast(str, family.get("name")).lower() == family_name.lower():
                return family
        return None

    @staticmethod
    def get_concentration_type(conc_type: str) -> Optional[JsonObject]:
        """Get concentration type details (EDP, EDT, etc.)"""
        data = DataLoader.load_fragrance_families()
        for conc in cast(list[JsonObject], data.get("concentration_types", [])):
            if cast(str, conc.get("type")).lower() == conc_type.lower():
                return conc
        return None

    @staticmethod
    def list_fragrance_families() -> list[Optional[str]]:
        """Get all fragrance families"""
        data = DataLoader.load_fragrance_families()
        families = cast(list[JsonObject], data.get("fragrance_families", []))
        return [cast(Optional[str], family.get("name")) for family in families]

    @staticmethod
    def list_all_compounds() -> list[JsonObject]:
        """Get all compounds"""
        compounds = DataLoader.load_compounds()
        return cast(list[JsonObject], compounds.get("compounds", []))

    @staticmethod
    def get_statistics() -> JsonObject:
        """Get data statistics"""
        compounds = DataLoader.load_compounds()
        families = DataLoader.load_fragrance_families()
        knowledge_files = DataLoader.list_knowledge_files()

        return {
            "total_compounds": len(compounds.get("compounds", [])),
            "total_fragrance_families": len(families.get("fragrance_families", [])),
            "concentration_types": len(families.get("concentration_types", [])),
            "knowledge_documents": len(knowledge_files),
            "data_files": {
                "compounds": str(DATA_DIR / "compounds.json"),
                "fragrance_reference": str(BACKEND_DATA_DIR / "reference" / "fragrance_reference.json"),
                "knowledge_base": str(KNOWLEDGE_DIR)
            }
        }

    @staticmethod
    @lru_cache(maxsize=1)
    def list_knowledge_files() -> list[str]:
        """List all markdown knowledge files"""
        knowledge_files: list[str] = []
        if KNOWLEDGE_DIR.exists():
            for md_file in KNOWLEDGE_DIR.glob("**/*.md"):
                relative_path = md_file.relative_to(KNOWLEDGE_DIR)
                knowledge_files.append(str(relative_path))
        return sorted(knowledge_files)

    @staticmethod
    def load_knowledge_file(filename: str) -> Optional[str]:
        """Load a knowledge markdown file by name"""
        # Refuse absolute, drive, UNC and ../ names before touching the disk.
        # On Windows, resolving a UNC name such as \\host\share\x.md opens a
        # network connection (sending the user's sign-in hash) even though
        # the containment check below would then refuse it.
        if _is_unsafe_relative_name(filename):
            return None
        try:
            # Resolve both sides (following symlinks) and refuse anything that
            # lands outside the knowledge folder: ../ segments, absolute paths
            # and links pointing elsewhere.
            knowledge_root = KNOWLEDGE_DIR.resolve()
            file_path = (knowledge_root / filename).resolve()
            if not file_path.is_relative_to(knowledge_root):
                return None
            if file_path.is_file() and file_path.suffix == ".md":
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to load knowledge file {filename}: {e}")
        return None

    @staticmethod
    def search_knowledge(query: str) -> KnowledgeSearchResult:
        """Search through knowledge files for query term"""
        results: KnowledgeSearchResult = {"files": [], "matches": []}
        query_lower = query.lower()

        knowledge_files = DataLoader.list_knowledge_files()
        for filename in knowledge_files:
            content = DataLoader.load_knowledge_file(filename)
            if content and query_lower in content.lower():
                results["files"].append(filename)
                # Find matching lines
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        results["matches"].append({
                            "file": filename,
                            "line_number": i + 1,
                            "content": line.strip()
                        })

        return results
