"""Tests for data loader"""

import pytest
from app.services.data_loader import DataLoader


def test_load_compounds():
    """Test loading compounds database"""
    compounds = DataLoader.load_compounds()
    assert "compounds" in compounds
    assert len(compounds["compounds"]) > 0


def test_load_fragrance_families():
    """Test loading fragrance families"""
    data = DataLoader.load_fragrance_families()
    assert "fragrance_families" in data
    assert "concentration_types" in data


def test_get_compound_by_cas():
    """Test getting compound by CAS number"""
    # Linalool CAS
    compound = DataLoader.get_compound_by_cas("78-70-6")
    assert compound is not None
    assert compound.get("name") == "Linalool"


def test_get_compound_by_name():
    """Test getting compound by name"""
    compound = DataLoader.get_compound_by_name("Vanillin")
    assert compound is not None
    assert compound.get("cas") == "121-33-5"


def test_search_compounds():
    """Test searching compounds"""
    results = DataLoader.search_compounds("citrus")
    assert len(results) > 0


def test_get_statistics():
    """Test getting data statistics"""
    stats = DataLoader.get_statistics()
    assert stats["total_compounds"] > 0
    assert stats["total_fragrance_families"] > 0
    assert "data_files" in stats
    assert "knowledge_documents" in stats


def test_list_knowledge_files():
    """Test listing knowledge files"""
    files = DataLoader.list_knowledge_files()
    assert isinstance(files, list)
    assert len(files) > 0
    assert all(isinstance(f, str) for f in files)


def test_load_knowledge_file():
    """Test loading a knowledge file"""
    files = DataLoader.list_knowledge_files()
    if files:
        content = DataLoader.load_knowledge_file(files[0])
        assert content is not None
        assert isinstance(content, str)
        assert len(content) > 0


def test_load_nonexistent_knowledge_file():
    """Test loading non-existent knowledge file returns None"""
    content = DataLoader.load_knowledge_file("nonexistent_file_xyz.md")
    assert content is None


def test_search_knowledge():
    """Test searching knowledge base"""
    results = DataLoader.search_knowledge("chemical")
    assert isinstance(results, dict)
    assert "files" in results
    assert "matches" in results
    assert isinstance(results["files"], list)
    assert isinstance(results["matches"], list)