"""
JSONExporter for Export & Reporting Engine.
Exports complete CasePackage payload as a canonical JSON string or dictionary with zero information loss.
"""
import json
from typing import Dict, Any
from incident_intelligence.export.case_package import CasePackage

class JSONExporter:
    """Exports CasePackage into canonical JSON string representation."""

    def export_dict(self, case_package: CasePackage) -> Dict[str, Any]:
        """Convert CasePackage into nested dictionary representation."""
        return case_package.to_dto().to_dict()

    def export_json(self, case_package: CasePackage, formatted: bool = True) -> str:
        """Serialize CasePackage to JSON string."""
        payload = self.export_dict(case_package)
        if formatted:
            return json.dumps(payload, indent=2, sort_keys=True)
        return json.dumps(payload, sort_keys=True, separators=(',', ':'))
