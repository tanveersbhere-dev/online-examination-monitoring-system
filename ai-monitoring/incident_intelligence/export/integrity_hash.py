"""
IntegrityHash Helper for Export & Reporting Engine.
Computes and verifies SHA-256 hashes over canonical JSON payloads.
"""
import hashlib
import json
from typing import Dict, Any

class IntegrityHash:
    """Computes and verifies cryptographic SHA-256 digests over case data."""

    @staticmethod
    def compute_hash(payload: Dict[str, Any]) -> str:
        """
        Compute deterministic SHA-256 hex digest over sorted canonical JSON bytes.
        """
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hashlib.sha256(canonical_json).hexdigest()

    @staticmethod
    def verify_hash(payload: Dict[str, Any], expected_hash: str) -> bool:
        """
        Verify that computed payload SHA-256 matches expected digest.
        """
        computed = IntegrityHash.compute_hash(payload)
        return computed.lower() == expected_hash.lower()
