"""Formulation engine: Blend science and artistry."""

from dataclasses import dataclass, field
from .validator import validate_formula, check_compatibility, get_compounds

@dataclass
class Formula:
    name: str
    ingredients: dict[str, float] = field(default_factory=dict)
    notes: str = ""
    
    def add(self, ingredient: str, percentage: float) -> tuple[bool, str]:
        """Add ingredient with pre-validation."""
        test_formula = {**self.ingredients, ingredient: percentage}
        result = validate_formula(test_formula)
        
        if not result.valid:
            return False, result.errors[0]
        
        self.ingredients[ingredient] = percentage
        msg = f"Added {ingredient} at {percentage}%"
        if result.warnings:
            msg += f" (Note: {result.warnings[0]})"
        return True, msg
    
    def remove(self, ingredient: str) -> bool:
        if ingredient in self.ingredients:
            del self.ingredients[ingredient]
            return True
        return False
    
    def get_balance(self) -> dict:
        """Analyze note distribution."""
        compounds = get_compounds()
        balance = {"top": 0, "heart": 0, "base": 0}
        
        for ing, pct in self.ingredients.items():
            compound = compounds.get(ing.lower())
            if compound:
                balance[compound["note"]] += pct
        
        total = sum(balance.values()) or 1
        return {k: round(v/total*100, 1) for k, v in balance.items()}
    
    def suggest_next(self) -> list[str]:
        """Suggest ingredients to improve formula."""
        compounds = get_compounds()
        balance = self.get_balance()
        suggestions = []
        
        # Find weak areas
        if balance["base"] < 30:
            suggestions.append("Add base notes for longevity: Iso E Super, Galaxolide, Vanillin")
        if balance["top"] < 15:
            suggestions.append("Add top notes for impact: Limonene, Benzyl Acetate, Citral")
        if balance["heart"] < 25:
            suggestions.append("Add heart notes for body: Linalool, Hedione, Eugenol")
        
        # Suggest complementary ingredients
        current_scents = set()
        for ing in self.ingredients:
            compound = compounds.get(ing.lower())
            if compound:
                current_scents.update(compound.get("blends_with", []))
        
        if current_scents:
            suggestions.append(f"Consider blending with: {', '.join(list(current_scents)[:5])}")
        
        return suggestions if suggestions else ["Formula is well balanced!"]
    
    def export(self) -> str:
        """Export formula as formatted text."""
        lines = [f"# {self.name}", "", "## Ingredients", ""]
        
        total = sum(self.ingredients.values())
        for ing, pct in sorted(self.ingredients.items(), key=lambda x: -x[1]):
            lines.append(f"- {ing}: {pct}% ({pct/total*100:.1f}% of concentrate)")
        
        lines.extend(["", f"**Total concentration:** {total}%", ""])
        
        balance = self.get_balance()
        lines.extend([
            "## Structure",
            f"- Top: {balance['top']}%",
            f"- Heart: {balance['heart']}%", 
            f"- Base: {balance['base']}%"
        ])
        
        result = validate_formula(self.ingredients)
        if result.warnings:
            lines.extend(["", "## Warnings"])
            for w in result.warnings:
                lines.append(f"- {w}")
        
        if self.notes:
            lines.extend(["", "## Notes", self.notes])
        
        return "\n".join(lines)
