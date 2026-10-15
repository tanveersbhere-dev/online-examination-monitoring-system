"""
InMemoryReviewRepository for Review Intelligence Engine.
Stores ReviewPackage aggregates in memory.
"""
from typing import Dict, Any, Optional, List
from incident_intelligence.review.review_package import ReviewPackage
from incident_intelligence.review.review_status import ReviewStatusEnum

class InMemoryReviewRepository:
    """In-memory storage adapter for ReviewPackage objects."""

    def __init__(self):
        self._packages: Dict[str, ReviewPackage] = {}
        self._incident_map: Dict[str, str] = {}  # incident_id -> package_id

    def save(self, package: ReviewPackage) -> None:
        """Save or update a review package."""
        self._packages[package.package_id] = package
        self._incident_map[package.incident_id] = package.package_id

    def get_by_package_id(self, package_id: str) -> Optional[ReviewPackage]:
        """Fetch review package by package_id."""
        return self._packages.get(package_id)

    def get_by_incident_id(self, incident_id: str) -> Optional[ReviewPackage]:
        """Fetch review package by incident_id."""
        pkg_id = self._incident_map.get(incident_id)
        if pkg_id:
            return self._packages.get(pkg_id)
        return None

    def list_by_status(self, status: ReviewStatusEnum) -> List[ReviewPackage]:
        """Filter review packages by status."""
        return [
            pkg for pkg in self._packages.values()
            if pkg.review_status == status or (hasattr(pkg.review_status, 'value') and pkg.review_status.value == status.value)
        ]

    def list_all(self) -> List[ReviewPackage]:
        """List all review packages."""
        return list(self._packages.values())

    def clear(self) -> None:
        """Clear repository."""
        self._packages.clear()
        self._incident_map.clear()
