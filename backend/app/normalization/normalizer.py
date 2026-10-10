"""Transaction normalizer: converts raw workbook rows to CanonicalTransaction.

Handles:
- Decimal conversion for amount fields (preserving precision)
- Date normalization
- Missing vs zero vs false distinction
- Cell provenance tracking
- Sparse transaction handling (only populated fields included)
- Unknown fields preserved in metadata
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.ingestion.column_mapper import (
    CANONICAL_ACCOUNT_FIELDS,
    CANONICAL_AMOUNT_FIELDS,
    CANONICAL_DOCUMENT_FIELDS,
    CANONICAL_EXPENSE_FIELDS,
    CANONICAL_HR_FIELDS,
    CANONICAL_INVENTORY_FIELDS,
    CANONICAL_ITEM_FIELDS,
    CANONICAL_JOBWORK_FIELDS,
    CANONICAL_META_FIELDS,
    CANONICAL_PARTY_FIELDS,
    CANONICAL_REFERENCE_FIELDS,
    CANONICAL_RETURN_FIELDS,
    CANONICAL_TAX_FIELDS,
    CANONICAL_TRADE_FIELDS,
    ColumnMappingResult,
)
from app.ingestion.reader import RawRow


@dataclass
class NormalizedSignal:
    """A single normalized financial signal with provenance."""

    canonical_name: str
    value: Any
    original_value: Any
    source_coordinate: str
    source_header: str
    status: str  # "observed", "derived", "parse_error"
    parse_warning: str | None = None


@dataclass
class NormalizedTransaction:
    """A fully normalized transaction with provenance.

    This is a rich intermediate representation that feeds into
    CanonicalTransaction construction.
    """

    transaction_id: str
    source_sheet: str
    physical_row: int
    source_sha256: str

    # Normalized fields grouped by category
    document: dict[str, Any] = field(default_factory=dict)
    parties: dict[str, Any] = field(default_factory=dict)
    items: dict[str, Any] = field(default_factory=dict)
    amounts: dict[str, Decimal | None] = field(default_factory=dict)
    tax: dict[str, Any] = field(default_factory=dict)
    accounts: dict[str, Any] = field(default_factory=dict)
    references: dict[str, Any] = field(default_factory=dict)
    returns: dict[str, Any] = field(default_factory=dict)
    inventory: dict[str, Any] = field(default_factory=dict)
    hr: dict[str, Any] = field(default_factory=dict)
    trade: dict[str, Any] = field(default_factory=dict)
    jobwork: dict[str, Any] = field(default_factory=dict)
    expense: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    # Unmapped / unknown fields preserved as metadata
    extra_fields: dict[str, Any] = field(default_factory=dict)

    # Provenance
    signals: list[NormalizedSignal] = field(default_factory=list)
    populated_field_count: int = 0
    total_field_count: int = 0
    missing_paths: list[str] = field(default_factory=list)
    parse_issues: list[str] = field(default_factory=list)
    data_quality_warnings: list[str] = field(default_factory=list)

    # Target label (for evaluation only — NEVER for inference)
    target_label: str | None = None


def _safe_decimal(value: Any, coordinate: str) -> tuple[Decimal | None, str | None]:
    """Convert a value to Decimal safely. Returns (decimal_value, warning)."""
    if value is None:
        return None, None
    if isinstance(value, bool):
        # bool before int check since bool is subclass of int
        return None, f"Boolean value at {coordinate} cannot be converted to Decimal"
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value)), None
        except (InvalidOperation, ValueError) as e:
            return None, f"Cannot convert numeric {value} at {coordinate}: {e}"
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("₹", "").replace("$", "")
        if not cleaned or cleaned == "-":
            return None, None
        try:
            return Decimal(cleaned), None
        except (InvalidOperation, ValueError):
            return None, f"Cannot parse amount string '{value}' at {coordinate}"
    if isinstance(value, Decimal):
        return value, None
    return None, f"Unexpected type {type(value).__name__} for amount at {coordinate}"


def _safe_date_str(value: Any, coordinate: str) -> tuple[str | None, str | None]:
    """Convert a date/datetime to ISO string. Returns (date_str, warning)."""
    if value is None:
        return None, None
    if isinstance(value, datetime):
        return value.date().isoformat(), None
    if isinstance(value, date):
        return value.isoformat(), None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None, None
        # Try ISO format first
        if re.match(r"^\d{4}-\d{2}-\d{2}", cleaned):
            return cleaned[:10], None
        # Try common formats (DD/MM/YYYY, MM/DD/YYYY are ambiguous!)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat(), None
            except ValueError:
                continue
        # Ambiguous format warning
        if re.match(r"^\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}$", cleaned):
            return cleaned, f"Ambiguous date format at {coordinate}: '{cleaned}'"
        return cleaned, None
    return str(value), f"Unexpected type for date at {coordinate}: {type(value).__name__}"


def _safe_string(value: Any) -> str | None:
    """Convert a value to string, preserving None and empty distinctions."""
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value)
    s = str(value).strip()
    return s if s else None


# Date-type canonical fields
DATE_FIELDS = {
    "document_date",
    "transaction_date",
    "invoice_date",
    "payment_due_date",
}

# Amount-type canonical fields (Decimal)
AMOUNT_FIELDS = (
    CANONICAL_AMOUNT_FIELDS
    | CANONICAL_TAX_FIELDS
    | {
        "unit_price",
        "exchange_rate_inr",
    }
)

# Quantity fields (also Decimal)
QUANTITY_FIELDS = {
    "quantity",
    "ordered_quantity",
    "received_quantity",
    "dispatched_quantity",
    "returned_quantity",
    "rejected_quantity",
    "stock_book_qty",
    "stock_counted_qty",
    "stock_difference",
    "days_present",
    "days_absent",
    "overtime_hours",
}


def _categorize_field(canonical_name: str) -> str:
    """Return the category bucket for a canonical field name."""
    if canonical_name in CANONICAL_DOCUMENT_FIELDS:
        return "document"
    if canonical_name in CANONICAL_PARTY_FIELDS:
        return "parties"
    if canonical_name in CANONICAL_ITEM_FIELDS:
        return "items"
    if canonical_name in CANONICAL_AMOUNT_FIELDS:
        return "amounts"
    if canonical_name in CANONICAL_TAX_FIELDS:
        return "tax"
    if canonical_name in CANONICAL_ACCOUNT_FIELDS:
        return "accounts"
    if canonical_name in CANONICAL_REFERENCE_FIELDS:
        return "references"
    if canonical_name in CANONICAL_RETURN_FIELDS:
        return "returns"
    if canonical_name in CANONICAL_INVENTORY_FIELDS:
        return "inventory"
    if canonical_name in CANONICAL_HR_FIELDS:
        return "hr"
    if canonical_name in CANONICAL_TRADE_FIELDS:
        return "trade"
    if canonical_name in CANONICAL_JOBWORK_FIELDS:
        return "jobwork"
    if canonical_name in CANONICAL_EXPENSE_FIELDS:
        return "expense"
    if canonical_name in CANONICAL_META_FIELDS:
        return "meta"
    return "extra_fields"


def normalize_row(
    raw_row: RawRow,
    mapping: ColumnMappingResult,
    source_sha256: str,
    row_index: int,
) -> NormalizedTransaction:
    """Normalize a single raw row into a NormalizedTransaction.

    Only processes populated cells. Missing fields stay missing (not defaulted).
    Distinguishes zero from missing. Preserves unknown fields.
    """
    # Generate a transaction ID from sheet + row
    tx_id = f"{source_sha256[:12]}:{raw_row.sheet_name}:{raw_row.physical_row}"

    result = NormalizedTransaction(
        transaction_id=tx_id,
        source_sheet=raw_row.sheet_name,
        physical_row=raw_row.physical_row,
        source_sha256=source_sha256,
        target_label=raw_row.target_label,
    )

    result.total_field_count = len(raw_row.cells)
    populated = 0

    populated_sources: dict[str, list] = {}
    for source_cell in raw_row.cells:
        key = mapping.source_to_canonical.get(source_cell.column_header.strip())
        if key and source_cell.value is not None and source_cell.value != "":
            populated_sources.setdefault(key, []).append(source_cell)
    for key, cells in populated_sources.items():
        if key != "narration" and len(cells) > 1 and len({repr(c.value) for c in cells}) > 1:
            result.parse_issues.append(
                f"MULTIPLE_SOURCE_VALUES:{key}:" + ",".join(c.coordinate for c in cells)
            )

    for cell in raw_row.cells:
        if cell.value is None:
            continue

        populated += 1
        header = cell.column_header.strip()
        canonical = mapping.source_to_canonical.get(header)

        if canonical is None:
            # Unknown/unmapped field — preserve in extra_fields
            result.extra_fields[header] = cell.value
            result.signals.append(
                NormalizedSignal(
                    canonical_name=f"unmapped:{header}",
                    value=cell.value,
                    original_value=cell.value,
                    source_coordinate=cell.coordinate,
                    source_header=header,
                    status="observed",
                )
            )
            continue

        signal_name = f"{canonical}[{header}]" if len(populated_sources.get(canonical, [])) > 1 else canonical

        # Normalize based on field type
        normalized_value: Any = None
        warning: str | None = None

        if canonical in DATE_FIELDS:
            normalized_value, warning = _safe_date_str(cell.value, cell.coordinate)
        elif canonical in AMOUNT_FIELDS or canonical in QUANTITY_FIELDS:
            normalized_value, warning = _safe_decimal(cell.value, cell.coordinate)
        else:
            normalized_value = _safe_string(cell.value)

        if warning:
            result.parse_issues.append(warning)

        if normalized_value is None and cell.value is not None:
            # Value existed but couldn't be parsed
            normalized_value = _safe_string(cell.value)
            if normalized_value is not None:
                result.signals.append(
                    NormalizedSignal(
                        canonical_name=signal_name,
                        value=normalized_value,
                        original_value=cell.value,
                        source_coordinate=cell.coordinate,
                        source_header=header,
                        status="parse_error",
                        parse_warning=warning,
                    )
                )
        else:
            status = "observed"
            result.signals.append(
                NormalizedSignal(
                    canonical_name=signal_name,
                    value=normalized_value,
                    original_value=cell.value,
                    source_coordinate=cell.coordinate,
                    source_header=header,
                    status=status,
                )
            )

        # Place the value in the correct category bucket
        if normalized_value is not None:
            category = _categorize_field(canonical)
            bucket = getattr(result, category)
            bucket[signal_name] = normalized_value

    result.populated_field_count = populated
    return result


def normalize_workbook_data(
    rows: list[RawRow],
    mapping: ColumnMappingResult,
    source_sha256: str,
) -> list[NormalizedTransaction]:
    """Normalize all rows from a workbook into NormalizedTransactions.

    Returns a list preserving the original row order.
    """
    return [normalize_row(raw_row, mapping, source_sha256, idx) for idx, raw_row in enumerate(rows)]


def build_prompt_context(
    transaction: NormalizedTransaction,
    max_fields: int = 80,
) -> dict[str, Any]:
    """Build a context representation for the LLM prompt.

    Only includes populated fields. Does NOT include the target label.
    Designed for sparse transactions where most fields are empty.
    """
    context: dict[str, Any] = {}

    # Add fields from each category, skipping empty dicts
    for category in [
        "document",
        "parties",
        "items",
        "amounts",
        "tax",
        "accounts",
        "references",
        "returns",
        "inventory",
        "hr",
        "trade",
        "jobwork",
        "expense",
    ]:
        bucket = getattr(transaction, category)
        if bucket:
            for key, value in bucket.items():
                if value is not None:
                    # Convert Decimal to string for JSON serialization
                    if isinstance(value, Decimal):
                        context[key] = str(value)
                    else:
                        context[key] = value

    # Include unmapped fields if they seem relevant
    if transaction.extra_fields:
        for key, value in transaction.extra_fields.items():
            if value is not None and len(context) < max_fields:
                context[f"_extra:{key}"] = _safe_string(value)

    # Truncate if too many fields
    if len(context) > max_fields:
        # Keep the first max_fields entries (they're ordered by category priority)
        keys = list(context.keys())[:max_fields]
        context = {k: context[k] for k in keys}

    return context
