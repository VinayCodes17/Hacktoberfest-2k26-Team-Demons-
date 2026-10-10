"""Ingestion pipeline: end-to-end workbook loading, detection, mapping, normalization.

Provides a single entry point that:
1. Validates and profiles the workbook safely
2. Auto-detects the schema format
3. Builds column mappings
4. Reads rows with cell provenance
5. Normalizes transactions
6. Extracts target labels separately (for evaluation only)

Also provides utilities to split the organizer workbook into unlabeled input
and private label key files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.ingestion.column_mapper import ColumnMappingResult, build_column_mapping
from app.ingestion.profiler import WorkbookProfile, profile_workbook
from app.ingestion.reader import WorkbookData, read_workbook
from app.ingestion.schema_detector import SchemaDetectionResult, detect_schema
from app.normalization.normalizer import (
    NormalizedTransaction,
    normalize_workbook_data,
)


@dataclass
class IngestionResult:
    """Complete result of the ingestion pipeline."""

    # Source info
    filename: str
    source_sha256: str

    # Detection
    profile: WorkbookProfile
    detection: SchemaDetectionResult
    mapping: ColumnMappingResult

    # Data
    workbook_data: WorkbookData
    transactions: list[NormalizedTransaction]

    # Summary
    total_rows: int
    populated_fields_range: tuple[int, int]  # (min, max) populated fields per row

    # Labels (for evaluation only — NEVER for inference)
    has_target_labels: bool
    target_label_count: int
    unique_labels: list[str]

    # Issues
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def ingest_workbook(
    path: Path,
    sheet_name: str | None = None,
    header_row: int = 1,
    user_mapping_overrides: dict[str, str] | None = None,
) -> IngestionResult:
    """Full ingestion pipeline: profile → detect → map → read → normalize.

    Arguments:
        path: Path to the XLSX file.
        sheet_name: Sheet to read. If None, auto-detected from format.
        header_row: 1-based row number of headers.
        user_mapping_overrides: Optional dict mapping source headers to canonical fields.

    Returns:
        IngestionResult with all data, mappings, and provenance.
    """
    all_errors: list[str] = []
    all_warnings: list[str] = []

    # Step 1: Profile the workbook
    profile = profile_workbook(path)
    if profile.errors:
        all_errors.extend(profile.errors)
        return _empty_result(path.name, profile, all_errors, all_warnings)

    all_warnings.extend(profile.warnings)

    # Step 2: Detect schema format
    detection = detect_schema(profile)

    # Step 3: Determine which sheet to read
    if sheet_name is None:
        if detection.matched_sheet:
            sheet_name = detection.matched_sheet
        elif profile.sheet_profiles:
            sheet_name = profile.sheet_profiles[0].name
            all_warnings.append(f"No format detected. Defaulting to first sheet: '{sheet_name}'")
        else:
            all_errors.append("No sheets found in workbook")
            return _empty_result(path.name, profile, all_errors, all_warnings, detection=detection)

    # Step 4: Build column mapping
    selected_profile = None
    for sp in profile.sheet_profiles:
        if sp.name == sheet_name:
            selected_profile = sp
            break

    if selected_profile is None:
        all_errors.append(f"Sheet '{sheet_name}' not found in profile")
        return _empty_result(path.name, profile, all_errors, all_warnings, detection=detection)

    mapping = build_column_mapping(
        headers=selected_profile.headers,
        format_type=detection.detected_format,
        user_mapping_overrides=user_mapping_overrides,
    )
    all_warnings.extend(mapping.warnings)
    if mapping.ambiguous_mappings:
        all_warnings.extend(mapping.ambiguous_mappings)

    # Step 5: Read workbook rows with cell provenance
    workbook_data = read_workbook(path, sheet_name, header_row)
    if workbook_data.errors:
        all_errors.extend(workbook_data.errors)
        return _empty_result(
            path.name, profile, all_errors, all_warnings, detection=detection, mapping=mapping
        )

    all_warnings.extend(workbook_data.warnings)

    # Step 6: Normalize transactions
    transactions = normalize_workbook_data(
        rows=workbook_data.rows,
        mapping=mapping,
        source_sha256=workbook_data.source_sha256,
    )

    # Summary statistics
    populated_counts = [t.populated_field_count for t in transactions]
    min_pop = min(populated_counts) if populated_counts else 0
    max_pop = max(populated_counts) if populated_counts else 0

    # Target labels summary
    unique_labels = sorted(set(workbook_data.target_labels.values()))

    return IngestionResult(
        filename=path.name,
        source_sha256=workbook_data.source_sha256,
        profile=profile,
        detection=detection,
        mapping=mapping,
        workbook_data=workbook_data,
        transactions=transactions,
        total_rows=len(transactions),
        populated_fields_range=(min_pop, max_pop),
        has_target_labels=bool(workbook_data.target_labels),
        target_label_count=len(workbook_data.target_labels),
        unique_labels=unique_labels,
        errors=all_errors,
        warnings=all_warnings,
    )


def _empty_result(
    filename: str,
    profile: WorkbookProfile,
    errors: list[str],
    warnings: list[str],
    detection: SchemaDetectionResult | None = None,
    mapping: ColumnMappingResult | None = None,
) -> IngestionResult:
    """Create an empty result for error cases."""
    if detection is None:
        detection = SchemaDetectionResult(
            detected_format="unknown",
            confidence="low",
            matched_sheet=None,
            matched_headers=0,
            total_check_headers=0,
            reason="Not analyzed",
            selected_sheet_index=None,
        )
    if mapping is None:
        mapping = ColumnMappingResult(
            format_type="unknown",
            canonical_to_source={},
            source_to_canonical={},
            unmapped_columns=[],
            excluded_columns=[],
            ambiguous_mappings=[],
            warnings=[],
        )
    return IngestionResult(
        filename=filename,
        source_sha256=profile.source_sha256,
        profile=profile,
        detection=detection,
        mapping=mapping,
        workbook_data=WorkbookData(
            filename=filename,
            source_sha256="",
            sheet_name="",
            header_row=1,
            headers=[],
            rows=[],
            target_column_name=None,
            target_labels={},
            excluded_columns=[],
            unmapped_metadata_columns=[],
        ),
        transactions=[],
        total_rows=0,
        populated_fields_range=(0, 0),
        has_target_labels=False,
        target_label_count=0,
        unique_labels=[],
        errors=errors,
        warnings=warnings,
    )


def generate_ingestion_report(result: IngestionResult) -> dict[str, Any]:
    """Generate a JSON-serializable report from an ingestion result."""
    report: dict[str, Any] = {
        "filename": result.filename,
        "source_sha256": result.source_sha256,
        "detected_format": result.detection.detected_format,
        "detection_confidence": result.detection.confidence,
        "detection_reason": result.detection.reason,
        "selected_sheet": result.detection.matched_sheet,
        "total_rows": result.total_rows,
        "populated_fields_range": list(result.populated_fields_range),
        "canonical_fields_mapped": len(result.mapping.canonical_to_source),
        "unmapped_columns": result.mapping.unmapped_columns,
        "excluded_columns": result.mapping.excluded_columns,
        "has_target_labels": result.has_target_labels,
        "target_label_count": result.target_label_count,
        "unique_labels": result.unique_labels,
        "errors": result.errors,
        "warnings": result.warnings,
    }
    if result.transactions:
        # Sample of populated field counts
        counts = [t.populated_field_count for t in result.transactions]
        report["populated_field_stats"] = {
            "min": min(counts),
            "max": max(counts),
            "mean": round(sum(counts) / len(counts), 1),
        }
        # Parse issue summary
        all_issues = []
        for t in result.transactions:
            all_issues.extend(t.parse_issues)
        report["total_parse_issues"] = len(all_issues)
        if all_issues:
            report["sample_parse_issues"] = all_issues[:10]
    return report
