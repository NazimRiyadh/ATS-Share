"""
Entity Resolution Module with Dynamic Ontology.
Normalizes entities before storage to prevent duplicates.
Loads ontology from data/ontology.json.
Uses RapidFuzz for fast fuzzy matching.
"""

import logging
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass
from enum import Enum

from rapidfuzz import fuzz, process

from src.logging_config import get_logger

logger = get_logger(__name__)

class EntityType(str, Enum):
    """Core entity types for the ATS knowledge graph."""
    PERSON = "PERSON"
    SKILL = "SKILL"
    COMPANY = "COMPANY"
    ROLE = "ROLE"
    LOCATION = "LOCATION"
    CERTIFICATION = "CERTIFICATION"
    EDUCATION = "EDUCATION"


class RelationType(str, Enum):
    """Core relationship types for the ATS knowledge graph."""
    HAS_SKILL = "HAS_SKILL"
    WORKED_AT = "WORKED_AT"
    HAS_ROLE = "HAS_ROLE"
    LOCATED_IN = "LOCATED_IN"
    HAS_CERTIFICATION = "HAS_CERTIFICATION"
    HAS_EDUCATION = "HAS_EDUCATION"
    WORKED_WITH = "WORKED_WITH"  # Colleague/team relationships


@dataclass
class ResolvedEntity:
    """Result of entity resolution."""
    original: str
    canonical: str
    entity_type: EntityType
    confidence: float
    is_known: bool  # Whether it matched a known canonical entity


class EntityResolver:
    """
    Resolves and normalizes entities using fuzzy matching.
    Loads ontology dynamically from JSON.
    """
    
    ONTOLOGY_FILE = Path("data/ontology.json")
    
    def __init__(
        self,
        fuzzy_threshold: int = 85,  # Minimum similarity score (0-100)
        strict_mode: bool = False   # If True, reject unknown entities
    ):
        self.fuzzy_threshold = fuzzy_threshold
        self.strict_mode = strict_mode
        self._load_ontology()
        
    def _load_ontology(self):
        """Load ontology data from JSON file."""
        if not self.ONTOLOGY_FILE.exists():
            logger.warning(f"Ontology file not found at {self.ONTOLOGY_FILE}. Using empty defaults.")
            self._canonical_skills = set()
            self._canonical_companies = set()
            self._skill_variations = {}
            self._company_variations = {}
        else:
            try:
                with open(self.ONTOLOGY_FILE, "r") as f:
                    data = json.load(f)
                    self._canonical_skills = set(data.get("canonical_skills", []))
                    self._canonical_companies = set(data.get("canonical_companies", []))
                    self._skill_variations = data.get("skill_variations", {})
                    self._company_variations = data.get("company_variations", {})
                    logger.info(f"Loaded ontology: {len(self._canonical_skills)} skills, {len(self._canonical_companies)} companies")
            except Exception as e:
                logger.error(f"Failed to load ontology: {e}")
                # Fallback to empty
                self._canonical_skills = set()
                self._canonical_companies = set()
                self._skill_variations = {}
                self._company_variations = {}

        # Build lowercase lookup maps for faster matching
        self._skill_lookup = {s.lower(): s for s in self._canonical_skills}
        self._company_lookup = {c.lower(): c for c in self._canonical_companies}
        # Normalize keys in variations maps
        self._skill_variations = {k.lower(): v for k, v in self._skill_variations.items()}
        self._company_variations = {k.lower(): v for k, v in self._company_variations.items()}
    
    def resolve_skill(self, skill: str) -> ResolvedEntity:
        """
        Resolve a skill to its canonical form.
        """
        original = skill.strip()
        normalized = original.lower()
        
        # Step 1: Check exact match in variations
        if normalized in self._skill_variations:
            canonical = self._skill_variations[normalized]
            return ResolvedEntity(
                original=original,
                canonical=canonical,
                entity_type=EntityType.SKILL,
                confidence=1.0,
                is_known=True
            )
        
        # Step 2: Check exact match in canonical list
        if normalized in self._skill_lookup:
            canonical = self._skill_lookup[normalized]
            return ResolvedEntity(
                original=original,
                canonical=canonical,
                entity_type=EntityType.SKILL,
                confidence=1.0,
                is_known=True
            )
        
        # Step 3: Fuzzy match against canonical skills
        if self._skill_lookup:
            match = process.extractOne(
                normalized,
                self._skill_lookup.keys(),
                scorer=fuzz.ratio
            )
            
            if match and match[1] >= self.fuzzy_threshold:
                canonical = self._skill_lookup[match[0]]
                return ResolvedEntity(
                    original=original,
                    canonical=canonical,
                    entity_type=EntityType.SKILL,
                    confidence=match[1] / 100.0,
                    is_known=True
                )
        
        # Step 4: Unknown skill
        if self.strict_mode:
            return ResolvedEntity(
                original=original,
                canonical=original.title(),
                entity_type=EntityType.SKILL,
                confidence=0.0,
                is_known=False
            )
        
        # Clean and return as new skill
        canonical = self._clean_entity_name(original)
        return ResolvedEntity(
            original=original,
            canonical=canonical,
            entity_type=EntityType.SKILL,
            confidence=0.5,
            is_known=False
        )
    
    def resolve_company(self, company: str) -> ResolvedEntity:
        """
        Resolve a company to its canonical form.
        """
        original = company.strip()
        normalized = original.lower()
        
        # Remove common suffixes
        for suffix in [" inc", " inc.", " llc", " ltd", " corp", " corporation", " co", " company"]:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].strip()
        
        # Step 1: Check exact match in variations
        if normalized in self._company_variations:
            canonical = self._company_variations[normalized]
            return ResolvedEntity(
                original=original,
                canonical=canonical,
                entity_type=EntityType.COMPANY,
                confidence=1.0,
                is_known=True
            )
        
        # Step 2: Check exact match in canonical list
        if normalized in self._company_lookup:
            canonical = self._company_lookup[normalized]
            return ResolvedEntity(
                original=original,
                canonical=canonical,
                entity_type=EntityType.COMPANY,
                confidence=1.0,
                is_known=True
            )
        
        # Step 3: Fuzzy match
        if self._company_lookup:
            match = process.extractOne(
                normalized,
                self._company_lookup.keys(),
                scorer=fuzz.ratio
            )
            
            if match and match[1] >= self.fuzzy_threshold:
                canonical = self._company_lookup[match[0]]
                return ResolvedEntity(
                    original=original,
                    canonical=canonical,
                    entity_type=EntityType.COMPANY,
                    confidence=match[1] / 100.0,
                    is_known=True
                )
        
        # Unknown company
        canonical = self._clean_entity_name(original)
        return ResolvedEntity(
            original=original,
            canonical=canonical,
            entity_type=EntityType.COMPANY,
            confidence=0.5,
            is_known=False
        )
    
    def resolve_entity(
        self,
        entity: str,
        entity_type: str
    ) -> ResolvedEntity:
        """
        Resolve any entity based on its type.
        """
        entity_type_upper = entity_type.upper()
        
        if entity_type_upper == "SKILL":
            return self.resolve_skill(entity)
        elif entity_type_upper == "COMPANY" or entity_type_upper == "ORGANIZATION":
            return self.resolve_company(entity)
        else:
            # For other types, just clean the name
            canonical = self._clean_entity_name(entity)
            try:
                etype = EntityType(entity_type_upper)
            except ValueError:
                etype = EntityType.SKILL  # Default fallback
            
            return ResolvedEntity(
                original=entity,
                canonical=canonical,
                entity_type=etype,
                confidence=0.8,
                is_known=False
            )
    
    def validate_relationship_type(self, rel_type: str) -> Tuple[bool, str]:
        """
        Validate and normalize relationship type.
        """
        normalized = rel_type.upper().replace(" ", "_").replace("-", "_")
        
        # Map common variations
        rel_mappings = {
            "WORKS_AT": "WORKED_AT",
            "EMPLOYED_AT": "WORKED_AT",
            "KNOWS": "HAS_SKILL",
            "USES": "HAS_SKILL",
            "SKILLED_IN": "HAS_SKILL",
            "HAS_EXPERIENCE": "HAS_SKILL",
            "WORKS_AS": "HAS_ROLE",
            "POSITION": "HAS_ROLE",
            "CERTIFIED_IN": "HAS_CERTIFICATION",
            "LIVES_IN": "LOCATED_IN",
            "BASED_IN": "LOCATED_IN",
            "STUDIED_AT": "HAS_EDUCATION",
            "GRADUATED_FROM": "HAS_EDUCATION",
        }
        
        if normalized in rel_mappings:
            normalized = rel_mappings[normalized]
        
        # Check if it's a valid relationship type
        try:
            RelationType(normalized)
            return True, normalized
        except ValueError:
            # Default to most common relationship if unknown or log it
            return False, "HAS_SKILL"
    
    def _clean_entity_name(self, name: str) -> str:
        """Clean and normalize an entity name."""
        # Remove extra whitespace
        name = " ".join(name.split())
        # Title case
        name = name.title()
        return name


# Global resolver instance
_resolver: Optional[EntityResolver] = None


def get_entity_resolver() -> EntityResolver:
    """Get or create global entity resolver."""
    global _resolver
    if _resolver is None:
        _resolver = EntityResolver()
    return _resolver
