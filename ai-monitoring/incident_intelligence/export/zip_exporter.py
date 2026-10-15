"""
ZIPExporter for Export & Reporting Engine.
Packages investigation artifacts into an archived ZIP container.
"""
import io
import json
import zipfile
from typing import Dict, Any
from incident_intelligence.export.case_package import CasePackage
from incident_intelligence.export.pdf_exporter import PDFExporter

class ZIPExporter:
    """Packages CasePackage domain components into a ZIP archive buffer."""

    def __init__(self):
        self.pdf_exporter = PDFExporter()

    def export_zip_bytes(self, case_package: CasePackage) -> bytes:
        """
        Generate in-memory ZIP archive containing report.pdf and component JSON files.
        """
        buffer = io.BytesIO()

        dto_dict = case_package.to_dto().to_dict()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. report.pdf (Report text payload)
            report_text = self.pdf_exporter.generate_report_content(case_package)
            zf.writestr("report.pdf", report_text.encode('utf-8'))

            # 2. incident.json
            zf.writestr("incident.json", json.dumps(dto_dict.get("incident", {}), indent=2))

            # 3. timeline.json
            zf.writestr("timeline.json", json.dumps(dto_dict.get("timeline_events", []), indent=2))

            # 4. analytics.json
            zf.writestr("analytics.json", json.dumps(dto_dict.get("analytics", {}), indent=2))

            # 5. explanation.json
            zf.writestr("explanation.json", json.dumps(dto_dict.get("explanation", {}), indent=2))

            # 6. review.json
            zf.writestr("review.json", json.dumps(dto_dict.get("review", {}), indent=2))

            # 7. bookmarks.json
            replay_payload = dto_dict.get("replay", {}) or {}
            bookmarks_payload = replay_payload.get("bookmarks", [])
            zf.writestr("bookmarks.json", json.dumps(bookmarks_payload, indent=2))

            # 8. manifest.json
            zf.writestr("manifest.json", json.dumps(dto_dict.get("manifest", {}), indent=2))

        return buffer.getvalue()
