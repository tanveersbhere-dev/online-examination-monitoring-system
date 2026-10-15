"""
Automated AI Executive Monitoring Summary Generator.
Translates candidate proctoring violation logs and risk metrics into
clear, professional natural language reports for examiners.
"""
from typing import List, Dict, Any

def generate_ai_monitoring_summary(
    violations: List[Dict[str, Any]],
    final_risk_score: float,
    risk_level: str
) -> Dict[str, Any]:
    """
    Generates a structured, human-readable AI monitoring summary.
    """
    statements = []
    
    # 1. General Compliance Statement
    if risk_level == "LOW" or final_risk_score < 0.25:
        statements.append("Candidate remained compliant for most of the examination.")
    elif risk_level == "MEDIUM":
        statements.append("Candidate exhibited occasional proctoring anomalies during the examination.")
    elif risk_level == "HIGH":
        statements.append("Candidate exhibited significant suspicious behavioral patterns during the examination.")
    else:
        statements.append("Candidate engaged in multiple critical proctoring violations requiring immediate review.")

    # 2. Count specific violation types
    v_counts: Dict[str, int] = {}
    has_phone = 0
    has_multiple_faces = 0
    has_identity_mismatch = 0
    has_presentation_attack = 0
    looking_away_count = 0
    
    for v in violations:
        v_type = (v.get("violation_type") or "").upper()
        v_counts[v_type] = v_counts.get(v_type, 0) + 1
        
        if ("PHONE" in v_type and "EARPHONE" not in v_type and "HEADPHONE" not in v_type) or "MOBILE" in v_type:
            has_phone += 1
        if "MULTIPLE" in v_type or "PERSONS" in v_type:
            has_multiple_faces += 1
        if "PRESENTATION" in v_type or "SPOOF" in v_type or "ATTACK" in v_type:
            has_presentation_attack += 1
        if "LOOKING" in v_type or "GAZE" in v_type:
            looking_away_count += 1

    # 3. Mobile Phone summary
    if has_phone > 0:
        statements.append(f"{has_phone} confirmed mobile phone appearance(s) detected.")

    # 4. Presentation Attack summary
    if has_presentation_attack > 0:
        statements.append(f"CRITICAL: {has_presentation_attack} presentation attack / spoofing attempt(s) detected.")

    # 5. Looking away summary
    if looking_away_count > 0:
        statements.append("Looking away occurred repeatedly during the session.")
        
    # 6. Identity Verification summary
    if has_identity_mismatch > 0:
        statements.append(f"{has_identity_mismatch} identity verification / unauthorized face alert(s) recorded.")
    elif has_presentation_attack == 0:
        statements.append("Candidate identity remained verified throughout.")

    # 6. Multiple Faces summary
    if has_multiple_faces > 0:
        statements.append(f"{has_multiple_faces} multiple-person presence event(s) detected.")
    else:
        statements.append("No multiple-face violations occurred.")

    # 7. Overall integrity classification
    integrity_pct = int(max(0, min(100, (1.0 - final_risk_score) * 100)))
    statements.append(f"Overall examination integrity is classified as {risk_level} RISK (Integrity Index: {integrity_pct}%).")

    headline = statements[0]
    executive_summary_text = " ".join(statements)

    return {
        "headline": headline,
        "statements": statements,
        "executive_summary_text": executive_summary_text,
        "integrity_index": integrity_pct,
        "risk_level": risk_level,
        "final_risk_score": final_risk_score
    }
