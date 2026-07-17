"""Adapter between legacy JSON-based formula models and normalized lab schema components.

This is a pure transformation layer with no database dependency.
"""

from __future__ import annotations

from typing import Any


class LegacyFormulaAdapter:
    """Converts between legacy Perfume/Formula JSON ingredients and normalized component dicts."""

    @staticmethod
    def to_lab_components(ingredients: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert legacy JSON ingredient list to normalized component dicts.

        Args:
            ingredients: List of dicts with keys like name, percentage, grams, role,
                        stock_active_fraction (from Perfume.ingredients or Formula.ingredients).

        Returns:
            Component dictionaries with mass and percentage kept as distinct quantities.

        Raises:
            ValueError: If ingredients is empty or any entry lacks a name.
        """
        if not ingredients:
            raise ValueError("Ingredient list must not be empty")

        # Combine duplicate names (sum percentages and grams)
        combined: dict[str, dict[str, Any]] = {}
        for entry in ingredients:
            name = (entry.get("name") or "").strip()
            if not name:
                raise ValueError("Each ingredient must have a non-empty name")

            if name not in combined:
                combined[name] = {
                    "material_name": name,
                    "active_fraction": float(entry.get("stock_active_fraction", 1.0)),
                    "mass_g": None,
                    "role": entry.get("role"),
                    "position": len(combined) + 1,
                    "_percentage": 0.0,
                    "_grams": 0.0,
                    "_all_have_grams": True,
                }

            record = combined[name]
            record["_percentage"] += float(entry.get("percentage", 0.0))

            grams = entry.get("grams")
            if grams is not None:
                grams_value = float(grams)
                if grams_value < 0:
                    raise ValueError("Ingredient grams must be nonnegative")
                record["_grams"] += grams_value
            else:
                record["_all_have_grams"] = False

            # For active_fraction with duplicates, weight by percentage
            af = float(entry.get("stock_active_fraction", 1.0))
            old_pct = record["_percentage"] - float(entry.get("percentage", 0.0))
            total_pct = record["_percentage"]
            if total_pct > 0:
                record["active_fraction"] = (
                    record["active_fraction"] * old_pct + af * float(entry.get("percentage", 0.0))
                ) / total_pct

        # A missing measured mass remains unknown; percentage is never relabeled as grams.
        result = []
        for record in combined.values():
            result.append(
                {
                    "material_name": record["material_name"],
                    "active_fraction": record["active_fraction"],
                    "mass_g": record["_grams"] if record["_all_have_grams"] else None,
                    "percentage": record["_percentage"],
                    "role": record["role"],
                    "position": record["position"],
                }
            )

        return result

    @staticmethod
    def from_lab_components(components: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert normalized component dicts back to legacy JSON ingredient format.

        Args:
            components: List of dicts with keys: material_name, mass_g, role (position ignored).

        Returns:
            List of dicts with keys: name, percentage, role.
        """
        if not components:
            raise ValueError("Component list must not be empty")

        mass_values = [c.get("mass_g") for c in components]
        if all(value is not None for value in mass_values):
            weights = [float(c["mass_g"]) for c in components]
        elif all(c.get("percentage") is not None for c in components):
            weights = [float(c["percentage"]) for c in components]
        else:
            raise ValueError("Components must provide positive mass_g or percentage values")

        if any(weight < 0 for weight in weights) or sum(weights) <= 0:
            raise ValueError("Components must provide positive mass_g or percentage values")
        total = sum(weights)

        result = []
        for component, weight in zip(components, weights):
            name = (component.get("material_name") or "").strip()
            if not name:
                raise ValueError("Each component must have a non-empty material_name")

            percentage = round(weight / total * 100, 4)

            row = {"name": name, "percentage": percentage, "role": component.get("role")}
            if component.get("active_fraction") is not None:
                row["stock_active_fraction"] = component["active_fraction"]
            result.append(row)

        return result

    @staticmethod
    def round_trip(ingredients: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert legacy to normalized and back, verifying structural equivalence."""
        lab_components = LegacyFormulaAdapter.to_lab_components(ingredients)
        return LegacyFormulaAdapter.from_lab_components(lab_components)
