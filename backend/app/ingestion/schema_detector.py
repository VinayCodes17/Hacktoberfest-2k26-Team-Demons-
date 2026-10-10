"""Schema detection: identify workbook format (A: old synthetic, B: organizer).

Uses sheet names and header fingerprints to classify the workbook format
without hardcoding filenames. Supports unknown formats gracefully.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.ingestion.profiler import WorkbookProfile

FormatType = Literal["format_a", "format_b", "unknown"]


# ── Format A: old 500-row synthetic workbook ──────────────────────────────
# Key indicators: sheet named "Organizer_Ready_Input" with snake_case headers
FORMAT_A_SHEET = "Organizer_Ready_Input"
FORMAT_A_FINGERPRINT_HEADERS: set[str] = {
    "transaction_id",
    "document_reference",
    "transaction_date",
    "seller_name",
    "buyer_name",
    "invoice_number",
    "taxable_value",
    "narration",
    "currency",
    "debit_ledger",
    "credit_ledger",
}

# ── Format B: organizer 120-row test cases ────────────────────────────────
# Key indicators: sheet named "Test Cases" with human-readable headers
FORMAT_B_SHEET = "Test Cases"
FORMAT_B_FINGERPRINT_HEADERS: set[str] = {
    "PO Number",
    "Supplier",
    "Ordering Company",
    "Document Number",
    "Debit Side",
    "Credit Side",
    "Voucher Category",
    "Gross Salary",
    "Export Invoice No",
    "Import Bill No",
}


@dataclass
class SchemaDetectionResult:
    """Result of detecting the workbook format."""

    detected_format: FormatType
    confidence: str  # "high", "medium", "low"
    matched_sheet: str | None
    matched_headers: int
    total_check_headers: int
    reason: str
    selected_sheet_index: int | None  # Index into sheet_profiles


def detect_schema(profile: WorkbookProfile) -> SchemaDetectionResult:
    """Detect which format a profiled workbook uses.

    Returns a detection result with format type, confidence, and reasoning.
    Does not modify the profile or the workbook.
    """
    if profile.errors:
        return SchemaDetectionResult(
            detected_format="unknown",
            confidence="low",
            matched_sheet=None,
            matched_headers=0,
            total_check_headers=0,
            reason=f"Workbook has profiling errors: {'; '.join(profile.errors)}",
            selected_sheet_index=None,
        )

    # Try Format A
    for idx, sp in enumerate(profile.sheet_profiles):
        if sp.name == FORMAT_A_SHEET:
            header_set = {h.strip() for h in sp.headers if h.strip()}
            matched = FORMAT_A_FINGERPRINT_HEADERS & header_set
            total = len(FORMAT_A_FINGERPRINT_HEADERS)
            if len(matched) >= total * 0.7:
                confidence = "high" if len(matched) == total else "medium"
                return SchemaDetectionResult(
                    detected_format="format_a",
                    confidence=confidence,
                    matched_sheet=sp.name,
                    matched_headers=len(matched),
                    total_check_headers=total,
                    reason=f"Sheet '{FORMAT_A_SHEET}' found with {len(matched)}/{total} fingerprint headers",
                    selected_sheet_index=idx,
                )

    # Try Format B
    for idx, sp in enumerate(profile.sheet_profiles):
        if sp.name == FORMAT_B_SHEET:
            header_set = {h.strip() for h in sp.headers if h.strip()}
            matched = FORMAT_B_FINGERPRINT_HEADERS & header_set
            total = len(FORMAT_B_FINGERPRINT_HEADERS)
            if len(matched) >= total * 0.7:
                confidence = "high" if len(matched) == total else "medium"
                return SchemaDetectionResult(
                    detected_format="format_b",
                    confidence=confidence,
                    matched_sheet=sp.name,
                    matched_headers=len(matched),
                    total_check_headers=total,
                    reason=f"Sheet '{FORMAT_B_SHEET}' found with {len(matched)}/{total} fingerprint headers",
                    selected_sheet_index=idx,
                )

    # Fallback: try header fingerprinting on any sheet
    for idx, sp in enumerate(profile.sheet_profiles):
        header_set = {h.strip() for h in sp.headers if h.strip()}

        # Check format A headers on any sheet
        matched_a = FORMAT_A_FINGERPRINT_HEADERS & header_set
        if len(matched_a) >= len(FORMAT_A_FINGERPRINT_HEADERS) * 0.5:
            return SchemaDetectionResult(
                detected_format="format_a",
                confidence="low",
                matched_sheet=sp.name,
                matched_headers=len(matched_a),
                total_check_headers=len(FORMAT_A_FINGERPRINT_HEADERS),
                reason=f"Sheet '{sp.name}' has {len(matched_a)} format-A fingerprint headers (no canonical sheet name)",
                selected_sheet_index=idx,
            )

        # Check format B headers on any sheet
        matched_b = FORMAT_B_FINGERPRINT_HEADERS & header_set
        if len(matched_b) >= len(FORMAT_B_FINGERPRINT_HEADERS) * 0.5:
            return SchemaDetectionResult(
                detected_format="format_b",
                confidence="low",
                matched_sheet=sp.name,
                matched_headers=len(matched_b),
                total_check_headers=len(FORMAT_B_FINGERPRINT_HEADERS),
                reason=f"Sheet '{sp.name}' has {len(matched_b)} format-B fingerprint headers (no canonical sheet name)",
                selected_sheet_index=idx,
            )

    return SchemaDetectionResult(
        detected_format="unknown",
        confidence="low",
        matched_sheet=None,
        matched_headers=0,
        total_check_headers=0,
        reason="No matching sheet or header fingerprint found for known formats",
        selected_sheet_index=0 if profile.sheet_profiles else None,
    )
