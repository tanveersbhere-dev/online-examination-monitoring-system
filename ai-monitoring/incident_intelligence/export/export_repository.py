"""
InMemoryExportRepository for Export & Reporting Engine.
Stores CasePackage objects in memory.
"""
from typing import Dict, Any, Optional, List
from incident_intelligence.export.case_package import CasePackage

class InMemoryExportRepository:
    """In-memory storage adapter for CasePackage instances."""

    def __init__(self):
        self._packages_by_uuid: Dict[str, CasePackage] = {}
        self._packages_by_incident: Dict[str, CasePackage] = {}

    def save(self, case_package: CasePackage) -> None:
        """Save a CasePackage."""
        uuid_str = case_package.manifest.package_uuid
        inc_id = case_package.incident_dto.incident_id
        self._packages_by_uuid[uuid_str] = case_package
        self._packages_by_incident[inc_id] = case_package

    def get_by_uuid(self, package_uuid: str) -> Optional[CasePackage]:
        """Fetch CasePackage by UUID."""
        return self._packages_by_uuid.get(package_uuid)

    def get_by_incident_id(self, incident_id: str) -> Optional[CasePackage]:
        """Fetch CasePackage by incident_id."""
        return self._packages_by_incident.get(incident_id)

    def list_all(self) -> List[CasePackage]:
        """List all stored CasePackages."""
        return list(self._packages_by_uuid.values())

    def clear(self) -> None:
        """Clear repository."""
        self._packages_by_uuid.clear()
        self._packages_by_incident.clear()
