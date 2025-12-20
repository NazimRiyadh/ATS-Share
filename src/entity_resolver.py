"""
Entity Resolution Module with Fixed Ontology.
Normalizes entities before storage to prevent duplicates.
Uses RapidFuzz for fast fuzzy matching.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)


# =============================================================================
# FIXED ONTOLOGY
# =============================================================================

class EntityType(str, Enum):
    """Fixed entity types for the ATS knowledge graph."""
    PERSON = "PERSON"
    SKILL = "SKILL"
    COMPANY = "COMPANY"
    ROLE = "ROLE"
    LOCATION = "LOCATION"
    CERTIFICATION = "CERTIFICATION"
    EDUCATION = "EDUCATION"


class RelationType(str, Enum):
    """Fixed relationship types for the ATS knowledge graph."""
    HAS_SKILL = "HAS_SKILL"
    WORKED_AT = "WORKED_AT"
    HAS_ROLE = "HAS_ROLE"
    LOCATED_IN = "LOCATED_IN"
    HAS_CERTIFICATION = "HAS_CERTIFICATION"
    HAS_EDUCATION = "HAS_EDUCATION"
    WORKED_WITH = "WORKED_WITH"  # Colleague/team relationships


# =============================================================================
# CANONICAL SKILLS LIST (Top 250 - expandable over time)
# =============================================================================

CANONICAL_SKILLS = {
    # Programming Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "C", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Shell",
    "Bash", "PowerShell", "SQL", "NoSQL", "GraphQL",
    
    # Frontend
    "React", "Angular", "Vue.js", "Next.js", "Svelte", "HTML", "CSS", "SASS",
    "Tailwind CSS", "Bootstrap", "jQuery", "Redux", "Webpack", "Vite",
    
    # Backend
    "Node.js", "Django", "Flask", "FastAPI", "Spring Boot", "Express.js",
    "Ruby on Rails", "ASP.NET", "Laravel", "NestJS", "Gin", "Echo",
    
    # Databases
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
    "DynamoDB", "SQLite", "Oracle", "SQL Server", "Neo4j", "Firebase",
    
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Ansible",
    "Jenkins", "GitLab CI", "GitHub Actions", "CircleCI", "Nginx", "Apache",
    "Linux", "Unix", "Windows Server",
    
    # Data & ML
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Scikit-learn",
    "Pandas", "NumPy", "Keras", "NLP", "Computer Vision", "Data Science",
    "Data Analysis", "Data Engineering", "ETL", "Apache Spark", "Hadoop",
    "Airflow", "dbt", "Tableau", "Power BI", "Looker",
    
    # Mobile
    "iOS", "Android", "React Native", "Flutter", "SwiftUI", "Jetpack Compose",
    
    # Testing
    "Jest", "Pytest", "JUnit", "Selenium", "Cypress", "Playwright", "TDD",
    "BDD", "Unit Testing", "Integration Testing", "E2E Testing",
    
    # Architecture & Patterns
    "Microservices", "REST API", "GraphQL", "gRPC", "OAuth", "JWT",
    "CI/CD", "Agile", "Scrum", "Kanban", "Design Patterns", "SOLID",
    
    # Tools & Platforms
    "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence",
    "Slack", "VS Code", "IntelliJ", "Figma", "Postman",
    
    # Soft Skills
    "Leadership", "Communication", "Problem Solving", "Teamwork",
    "Project Management", "Time Management", "Critical Thinking",
    
    # Certifications (treated as skills for matching)
    "AWS Certified", "Azure Certified", "GCP Certified", "PMP",
    "Scrum Master", "CISSP", "CPA", "CFA", "Six Sigma",
}

# Variations mapping to canonical names
SKILL_VARIATIONS = {
    # JavaScript variations
    "js": "JavaScript",
    "javascript": "JavaScript",
    "java script": "JavaScript",
    "ecmascript": "JavaScript",
    
    # TypeScript variations
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "type script": "TypeScript",
    
    # React variations
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    
    # Node.js variations
    "nodejs": "Node.js",
    "node": "Node.js",
    "node.js": "Node.js",
    
    # Vue.js variations
    "vuejs": "Vue.js",
    "vue": "Vue.js",
    "vue.js": "Vue.js",
    
    # Angular variations
    "angularjs": "Angular",
    "angular.js": "Angular",
    
    # Python frameworks
    "django rest framework": "Django",
    "drf": "Django",
    
    # Databases
    "postgres": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "elastic": "Elasticsearch",
    "es": "Elasticsearch",
    
    # Cloud
    "amazon web services": "AWS",
    "amazon aws": "AWS",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "microsoft azure": "Azure",
    
    # DevOps
    "k8s": "Kubernetes",
    "kube": "Kubernetes",
    "github actions": "GitHub Actions",
    "gitlab ci/cd": "GitLab CI",
    
    # ML/AI
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "ai": "Machine Learning",
    "artificial intelligence": "Machine Learning",
    "natural language processing": "NLP",
    "cv": "Computer Vision",
    
    # C++ variations
    "c plus plus": "C++",
    "cplusplus": "C++",
    "cpp": "C++",
    
    # C# variations
    "csharp": "C#",
    "c sharp": "C#",
    
    # .NET variations
    "dotnet": "ASP.NET",
    ".net": "ASP.NET",
    ".net core": "ASP.NET",
    "aspnet": "ASP.NET",
}

# =============================================================================
# CANONICAL COMPANIES (Top tech companies - expandable)
# =============================================================================

CANONICAL_COMPANIES = {
    "Google", "Amazon", "Microsoft", "Apple", "Meta", "Facebook", "Netflix",
    "Tesla", "Uber", "Airbnb", "Salesforce", "Oracle", "IBM", "Intel",
    "Adobe", "Nvidia", "PayPal", "Shopify", "Stripe", "Twilio", "Zoom",
    "Slack", "Spotify", "LinkedIn", "Twitter", "X", "TikTok", "ByteDance",
    "Alibaba", "Tencent", "Samsung", "Sony", "Cisco", "VMware", "Dell",
    "HP", "Accenture", "Deloitte", "McKinsey", "BCG", "Bain", "Goldman Sachs",
    "Morgan Stanley", "JPMorgan", "Bank of America", "Citadel", "Jane Street",
}

COMPANY_VARIATIONS = {
    "fb": "Meta",
    "facebook": "Meta",
    "facebook inc": "Meta",
    "meta platforms": "Meta",
    "google inc": "Google",
    "google llc": "Google",
    "alphabet": "Google",
    "amazon.com": "Amazon",
    "amazon inc": "Amazon",
    "msft": "Microsoft",
    "microsoft corp": "Microsoft",
    "apple inc": "Apple",
    "x corp": "X",
    "twitter inc": "Twitter",
}


# =============================================================================
# ENTITY RESOLVER CLASS
# =============================================================================

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
    Enforces fixed ontology for entity and relationship types.
    """
    
    def __init__(
        self,
        fuzzy_threshold: int = 85,  # Minimum similarity score (0-100)
        strict_mode: bool = False   # If True, reject unknown entities
    ):
        self.fuzzy_threshold = fuzzy_threshold
        self.strict_mode = strict_mode
        
        # Build lowercase lookup maps for faster matching
        self._skill_lookup = {s.lower(): s for s in CANONICAL_SKILLS}
        self._company_lookup = {c.lower(): c for c in CANONICAL_COMPANIES}
        self._skill_variations = {k.lower(): v for k, v in SKILL_VARIATIONS.items()}
        self._company_variations = {k.lower(): v for k, v in COMPANY_VARIATIONS.items()}
    
    def resolve_skill(self, skill: str) -> ResolvedEntity:
        """
        Resolve a skill to its canonical form.
        
        Args:
            skill: Raw skill string from extraction
            
        Returns:
            ResolvedEntity with canonical name
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
        
        # Step 4: Unknown skill - return cleaned version or reject
        if self.strict_mode:
            return ResolvedEntity(
                original=original,
                canonical=original.title(),  # Title case for unknown
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
            confidence=0.5,  # Medium confidence for unknown
            is_known=False
        )
    
    def resolve_company(self, company: str) -> ResolvedEntity:
        """
        Resolve a company to its canonical form.
        
        Args:
            company: Raw company string from extraction
            
        Returns:
            ResolvedEntity with canonical name
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
        
        # Unknown company - return cleaned version
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
        
        Args:
            entity: Raw entity string
            entity_type: Type of entity (SKILL, COMPANY, etc.)
            
        Returns:
            ResolvedEntity with canonical name
        """
        entity_type_upper = entity_type.upper()
        
        if entity_type_upper == "SKILL":
            return self.resolve_skill(entity)
        elif entity_type_upper == "COMPANY":
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
        
        Args:
            rel_type: Raw relationship type from extraction
            
        Returns:
            Tuple of (is_valid, canonical_type)
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
            # Default to most common relationship
            logger.warning(f"Unknown relationship type '{rel_type}', defaulting to HAS_SKILL")
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
