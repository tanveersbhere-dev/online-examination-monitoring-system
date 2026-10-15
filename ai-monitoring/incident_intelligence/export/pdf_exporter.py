"""
PDFExporter for Export & Reporting Engine.
Generates reviewer-friendly investigation report documents containing summaries, evidence tables, and audit traces.
"""
from typing import Dict, Any
from incident_intelligence.export.case_package import CasePackage

class PDFExporter:
    """Generates structured reviewer-friendly PDF/HTML investigation report text."""

    def generate_report_content(self, case_package: CasePackage) -> str:
        """Construct structured investigation report text representation."""
        inc = case_package.incident_dto
        manifest = case_package.manifest

        lines = [
            "=========================================================================",
            "                      AI MONITORING PLAYGROUND                          ",
            "                  INCIDENT INVESTIGATION REPORT                         ",
            "=========================================================================",
            f"Package UUID    : {manifest.package_uuid}",
            f"Incident ID     : {inc.incident_id}",
            f"Incident Type   : {inc.incident_type}",
            f"Platform Version: {manifest.platform_version}",
            f"Integrity Hash  : {case_package.integrity_hash}",
            "-------------------------------------------------------------------------",
            "",
            "1. EXECUTIVE SUMMARY",
            "--------------------",
            f"  - Start Time      : {inc.start_time}",
            f"  - Total Duration  : {inc.duration:.1f} seconds",
            f"  - Peak Confidence : {inc.peak_confidence:.2f}",
            f"  - Current Risk    : {inc.current_risk:.1f}",
            f"  - Status          : {inc.status}",
            f"  - Severity        : {inc.severity}",
            "",
            "2. EVIDENCE TABLE",
            "-----------------",
        ]

        if case_package.evidence_references:
            lines.append(f"  {'ID':<10} {'Frame':<8} {'Time':<10} {'Importance':<12} {'Crop Type':<15}")
            lines.append(f"  {'-'*10} {'-'*8} {'-'*10} {'-'*12} {'-'*15}")
            for ref in case_package.evidence_references:
                lines.append(f"  {ref.evidence_id:<10} {ref.frame_number:<8} {ref.timestamp:<10.2f} {ref.importance:<12.2f} {ref.crop_type:<15}")
        else:
            lines.append("  (No evidence keyframes attached)")

        lines.extend([
            "",
            "3. TIMELINE SUMMARY",
            "-------------------",
        ])

        if case_package.timeline_events:
            for ev in case_package.timeline_events:
                lines.append(f"  Seq #{ev.sequence_number:<3} [{ev.timestamp:.2f}s] Event: {ev.event_type:<20} State: {ev.new_state or 'N/A'}")
        else:
            lines.append("  (No timeline events recorded)")

        lines.extend([
            "",
            "4. ANALYTICS SUMMARY",
            "--------------------",
        ])
        if case_package.analytics_snapshot_dto:
            a = case_package.analytics_snapshot_dto
            lines.append(f"  - Total Duration   : {a.metrics.total_duration_seconds}s")
            lines.append(f"  - Active Duration  : {a.metrics.active_duration_seconds}s")
            lines.append(f"  - Recovery Duration: {a.metrics.recovery_duration_seconds}s")
            lines.append(f"  - Confidence Trend : {a.confidence_analysis.trend} (Slope: {a.confidence_analysis.slope})")
            lines.append(f"  - Risk Velocity    : {a.risk_analysis.risk_velocity} dR/dt")
        else:
            lines.append("  (Analytics snapshot not available)")

        lines.extend([
            "",
            "5. EXPLAINABILITY SUMMARY",
            "------------------------",
        ])
        if case_package.explanation_package_dto:
            exp = case_package.explanation_package_dto
            lines.append(f"  - Reason Codes : {', '.join(rc['code'] for rc in exp.reason_codes)}")
            lines.append(f"  - Narrative    : {exp.deterministic_narrative}")
            lines.append(f"  - Reviewer Note: {exp.reviewer_summary.what_happened}")
        else:
            lines.append("  (Explanation package not available)")

        lines.extend([
            "",
            "6. HUMAN REVIEW SUMMARY",
            "-----------------------",
        ])
        if case_package.review_package_dto:
            rev = case_package.review_package_dto
            lines.append(f"  - Review Status  : {rev.review_status}")
            lines.append(f"  - Review Decision: {rev.review_decision}")
            lines.append(f"  - Notes Count    : {len(rev.notes)}")
            lines.append(f"  - Audit Trail    : {len(rev.audit_trail)} audit entries")
        else:
            lines.append("  (Review package not available)")

        lines.extend([
            "",
            "7. REPLAY BOOKMARK SUMMARY",
            "--------------------------",
        ])
        if case_package.replay_session_dto and case_package.replay_session_dto.bookmarks:
            for bm in case_package.replay_session_dto.bookmarks:
                lines.append(f"  - Bookmark [{bm['target_type']}]: {bm['label']} at Frame #{bm['frame_number']}")
        else:
            lines.append("  (No replay bookmarks created)")

        lines.extend([
            "",
            "=========================================================================",
            "                         END OF REPORT                                  ",
            "========================================================================="
        ])

        return "\n".join(lines)

    def export_pdf_bytes(self, case_package: CasePackage) -> bytes:
        """Return UTF-8 encoded report byte array."""
        text = self.generate_report_content(case_package)
        return text.encode('utf-8')
