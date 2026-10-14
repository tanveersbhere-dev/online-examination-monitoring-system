"""
Monitoring Summary Adapter
==========================
Generates executive AI monitoring summaries for finalized examination sessions
using PPRDataContract from ai_monitoring_playground.
"""
from typing import Dict, Any, List, Optional


class MonitoringSummaryAdapter:
    """
    Adapter producing standardized executive monitoring summaries for completed exams.
    """

    @staticmethod
    def generate_summary(
        violations: List[Dict[str, Any]],
        final_risk_score: float,
        risk_level: str,
        frames_processed: int = 0,
        total_evidence_count: int = 0
    ) -> Dict[str, Any]:
        """
        Builds standardized executive monitoring summary dictionary.
        """
        integrity_index = max(0, min(100, int((1.0 - final_risk_score) * 100)))

        statements = []
        if final_risk_score >= 0.75 or risk_level == "CRITICAL":
            statements.append("Critical proctoring anomalies were identified during the session.")
            headline = "Candidate examination flagged with critical risk."
        elif final_risk_score >= 0.50 or risk_level == "HIGH":
            statements.append("Elevated risk detected with behavioral or environment infractions.")
            headline = "Candidate examination flagged with high risk."
        elif final_risk_score >= 0.25 or risk_level == "MEDIUM":
            statements.append("Moderate behavioral infractions observed during examination.")
            headline = "Candidate examination completed with moderate risk."
        else:
            statements.append("No critical proctoring anomalies observed.")
            headline = "Candidate examination completed with clean integrity rating."

        executive_text = (
            f"Candidate examination completed with {len(violations)} proctoring violation(s) recorded. "
            f"Overall integrity classified as {risk_level} RISK (Integrity Index: {integrity_index}%)."
        )

        return {
            "headline": headline,
            "statements": statements,
            "executive_summary_text": executive_text,
            "integrity_index": integrity_index,
            "risk_level": risk_level,
            "final_risk_score": round(final_risk_score, 2),
            "frames_processed": frames_processed,
            "total_evidence_count": total_evidence_count
        }
