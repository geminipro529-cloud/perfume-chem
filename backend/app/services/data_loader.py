"""Data loading and caching utilities"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
BACKEND_DATA_DIR = Path(__file__).parent.parent.parent / "data"
KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent / "knowledge"


class DataLoader:
    """Load and cache reference data files"""

    @staticmethod
    @lru_cache(maxsize=1)
    def load_compounds() -> Dict[str, Any]:
        """Load chemical compounds database"""
        try:
            compounds_file = DATA_DIR / "compounds.json"
            if compounds_file.exists():
                with open(compounds_file, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded {len(data.get('compounds', []))} compounds")
                return data
        except Exception as e:
            logger.error(f"Failed to load compounds.json: {e}")
        return {"compounds": []}

    @staticmethod
    @lru_cache(maxsize=1)
    def load_fragrance_families() -> Dict[str, Any]:
        """Load fragrance classification data"""
        try:
            families_file = BACKEND_DATA_DIR / "reference" / "fragrance_reference.json"
            if families_file.exists():
                with open(families_file, 'r') as f:
                    data = json.load(f)
                logger.info(f"Loaded fragrance reference data")
                return data
        except Exception as e:
            logger.error(f"Failed to load fragrance_reference.json: {e}")
        return {"fragrance_families": [], "concentration_types": []}

    @staticmethod
    def get_compound_by_cas(cas_number: str) -> Optional[Dict[str, Any]]:
        """Get a compound by CAS number"""
        compounds = DataLoader.load_compounds()
        for compound in compounds.get("compounds", []):
            if compound.get("cas") == cas_number:
                return compound
        return None

    @staticmethod
    def get_compound_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Get a compound by name"""
        compounds = DataLoader.load_compounds()
        for compound in compounds.get("compounds", []):
            if compound.get("name").lower() == name.lower():
                return compound
        return None

    @staticmethod
    def search_compounds(query: str) -> list:
        """Search compounds by name or scent"""
        compounds = DataLoader.load_compounds()
        results = []
        query_lower = query.lower()

        for compound in compounds.get("compounds", []):
            # Search in name
            if query_lower in compound.get("name", "").lower():
                results.append(compound)
            # Search in scent profile
            elif any(query_lower in scent.lower() for scent in compound.get("scent", [])):
                results.append(compound)

        return results

    @staticmethod
    def get_fragrance_family(family_name: str) -> Optional[Dict[str, Any]]:
        """Get fragrance family details"""
        data = DataLoader.load_fragrance_families()
        for family in data.get("fragrance_families", []):
            if family.get("name").lower() == family_name.lower():
                return family
        return None

    @staticmethod
    def get_concentration_type(conc_type: str) -> Optional[Dict[str, Any]]:
        """Get concentration type details (EDP, EDT, etc.)"""
        data = DataLoader.load_fragrance_families()
        for conc in data.get("concentration_types", []):
            if conc.get("type").lower() == conc_type.lower():
                return conc
        return None

    @staticmethod
    def list_fragrance_families() -> list:
        """Get all fragrance families"""
        data = DataLoader.load_fragrance_families()
        return [f.get("name") for f in data.get("fragrance_families", [])]

    @staticmethod
    def list_all_compounds() -> list:
        """Get all compounds"""
        compounds = DataLoader.load_compounds()
        return compounds.get("compounds", [])

    @staticmethod
    def get_statistics() -> Dict[str, Any]:
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
    def list_knowledge_files() -> List[str]:
        """List all markdown knowledge files"""
        knowledge_files = []
        if KNOWLEDGE_DIR.exists():
            for md_file in KNOWLEDGE_DIR.glob("**/*.md"):
                relative_path = md_file.relative_to(KNOWLEDGE_DIR)
                knowledge_files.append(str(relative_path))
        return sorted(knowledge_files)

    @staticmethod
    def load_knowledge_file(filename: str) -> Optional[str]:
        """Load a knowledge markdown file by name"""
        try:
            file_path = KNOWLEDGE_DIR / filename
            if file_path.exists() and file_path.suffix == ".md":
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to load knowledge file {filename}: {e}")
        return None

    @staticmethod
    def search_knowledge(query: str) -> Dict[str, List[Dict[str, Any]]]:
        """Search through knowledge files for query term"""
        results = {"files": [], "matches": []}
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
