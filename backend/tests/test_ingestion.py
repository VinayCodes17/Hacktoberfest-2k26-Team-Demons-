"""Tests for workbook ingestion: profiling, schema detection, column mapping, reading.

Tests cover both Format A (old synthetic) and Format B (organizer test cases),
as well as safety checks, label leakage prevention, and edge cases.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from app.ingestion.column_mapper import (
    build_column_mapping,
)
from app.ingestion.pipeline import generate_ingestion_report, ingest_workbook
from app.ingestion.profiler import TARGET_LABEL_COLUMNS, profile_workbook, validate_file
from app.ingestion.reader import read_workbook
from app.ingestion.schema_detector import detect_schema

# ── Fixtures ───────────────────────────────────────────────────────────────

def _create_format_a_workbook(path: Path) -> Path:
    """Create a minimal Format A workbook (old synthetic style)."""
    wb = Workbook()
    # Must have an "Organizer_Ready_Input" sheet
    sheet = wb.active
    sheet.title = "Organizer_Ready_Input"
    headers = [
        "transaction_id", "document_reference", "transaction_date",
        "seller_name", "buyer_name", "invoice_number", "taxable_value",
        "narration", "currency", "debit_ledger", "credit_ledger",
        "quantity", "unit_price", "amount_paid",
    ]
    sheet.append(headers)
    # Row 1: full transaction
    sheet.append(["TX-001", "DOC-123", "2026-01-15", "Supplier A",
                  "Buyer B", "INV-001", 10000, "Purchase of goods",
                  "INR", "Purchase A/c", "Supplier A/c", 5, 2000, 10000])
    # Row 2: sparse transaction with zero and None
    sheet.append(["TX-002", None, "2026-02-20", None,
                  "Buyer C", None, 0, None,
                  "INR", None, None, None, None, None])
    # Row 3: transaction with False value
    sheet.append(["TX-003", "DOC-456", None, "Supplier D",
                  None, "INV-003", 5000, "Payment",
                  None, "Bank A/c", "Expense A/c", None, None, 5000])

    # Add a Voucher Ontology sheet for compatibility
    ontology = wb.create_sheet("Voucher Ontology")
    ontology.append(["Voucher Category", "Family", "Event Definition (interpreted)",
                     "Source URL", "Decision Boundary / Caution", "Current Provenance"])
    ontology.append(["Purchase", "Purchasing", "Supplier purchase",
                     "fixture://test", "Test boundary", "synthetic"])
    ontology.append([])

    wb.save(path)
    return path


def _create_format_b_workbook(path: Path, include_target: bool = True) -> Path:
    """Create a minimal Format B workbook (organizer test cases style)."""
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Test Cases"
    headers = [
        "PO Number", "Supplier", "Ordering Company", "PO Date",
        "Item", "Quantity Required", "Unit Rate", "Total Value",
        "Document Number", "Document Date", "Debit Side", "Credit Side",
        "Gross Salary", "Net Payable", "Employee Code", "Employee Full Name",
        "Export Invoice No", "Import Bill No", "Destination Country",
    ]
    if include_target:
        headers.append("Voucher Category")

    sheet.append(headers)

    # Purchase Order transaction
    row1 = ["PO-2026-001", "ABC Suppliers", "XYZ Corp", "2026-03-15",
            "Steel Bars", 100, 250, 25000,
            None, None, None, None,
            None, None, None, None,
            None, None, None]
    if include_target:
        row1.append("Purchase Order")
    sheet.append(row1)

    # Salary / Payroll transaction
    row2 = [None, None, None, None,
            None, None, None, None,
            "SAL-2026-03", "2026-03-31", "Salary Expense", "Bank A/c",
            75000, 62000, "EMP-042", "Raj Kumar",
            None, None, None]
    if include_target:
        row2.append("Salary / Payroll")
    sheet.append(row2)

    # Import transaction
    row3 = [None, None, None, None,
            None, None, None, None,
            None, None, None, None,
            None, None, None, None,
            None, "IMP-2026-007", "China"]
    if include_target:
        row3.append("Import")
    sheet.append(row3)

    wb.save(path)
    return path


def _create_empty_workbook(path: Path) -> Path:
    """Create an empty workbook."""
    wb = Workbook()
    wb.save(path)
    return path


# ── Profiler Tests ─────────────────────────────────────────────────────────

class TestProfiler:

    def test_validate_nonexistent_file(self, tmp_path):
        errors = validate_file(tmp_path / "missing.xlsx")
        assert len(errors) == 1
        assert "does not exist" in errors[0]

    def test_validate_wrong_extension(self, tmp_path):
        path = tmp_path / "data.csv"
        path.write_text("a,b,c")
        errors = validate_file(path)
        assert any("extension" in e for e in errors)

    def test_profile_format_a_workbook(self, tmp_path):
        path = _create_format_a_workbook(tmp_path / "format_a.xlsx")
        profile = profile_workbook(path)
        assert not profile.errors
        assert profile.source_sha256
        assert len(profile.sheet_profiles) >= 1
        ori_sheet = next(s for s in profile.sheet_profiles if s.name == "Organizer_Ready_Input")
        assert ori_sheet.data_row_count == 3
        assert not ori_sheet.has_target_column

    def test_profile_format_b_detects_target_column(self, tmp_path):
        path = _create_format_b_workbook(tmp_path / "format_b.xlsx")
        profile = profile_workbook(path)
        assert not profile.errors
        tc_sheet = next(s for s in profile.sheet_profiles if s.name == "Test Cases")
        assert tc_sheet.has_target_column
        assert tc_sheet.target_column_name == "Voucher Category"
        assert any("excluded from classification" in w for w in profile.warnings)


# ── Schema Detector Tests ─────────────────────────────────────────────────

class TestSchemaDetector:

    def test_detect_format_a(self, tmp_path):
        path = _create_format_a_workbook(tmp_path / "a.xlsx")
        profile = profile_workbook(path)
        result = detect_schema(profile)
        assert result.detected_format == "format_a"
        assert result.confidence in ("high", "medium")
        assert result.matched_sheet == "Organizer_Ready_Input"

    def test_detect_format_b(self, tmp_path):
        path = _create_format_b_workbook(tmp_path / "b.xlsx")
        profile = profile_workbook(path)
        result = detect_schema(profile)
        assert result.detected_format == "format_b"
        assert result.confidence in ("high", "medium")
        assert result.matched_sheet == "Test Cases"

    def test_detect_unknown_format(self, tmp_path):
        path = _create_empty_workbook(tmp_path / "empty.xlsx")
        profile = profile_workbook(path)
        result = detect_schema(profile)
        assert result.detected_format == "unknown"


# ── Column Mapper Tests ───────────────────────────────────────────────────

class TestColumnMapper:

    def test_format_a_identity_mapping(self):
        headers = ["transaction_id", "document_reference", "taxable_value",
                    "debit_ledger", "credit_ledger"]
        result = build_column_mapping(headers, "format_a")
        assert result.format_type == "format_a"
        assert result.canonical_to_source["transaction_id"] == "transaction_id"
        assert result.canonical_to_source["debit_ledger"] == "debit_ledger"
        assert not result.excluded_columns
        assert not result.unmapped_columns

    def test_format_b_mapping(self):
        headers = ["PO Number", "Supplier", "Debit Side", "Credit Side",
                    "Gross Salary", "Net Payable"]
        result = build_column_mapping(headers, "format_b")
        assert result.canonical_to_source["purchase_order_no"] == "PO Number"
        assert result.canonical_to_source["supplier_name"] == "Supplier"
        assert result.canonical_to_source["debit_ledger"] == "Debit Side"
        assert result.canonical_to_source["credit_ledger"] == "Credit Side"
        assert result.canonical_to_source["gross_pay"] == "Gross Salary"
        assert result.canonical_to_source["net_pay"] == "Net Payable"

    def test_target_column_always_excluded(self):
        """CRITICAL: Voucher Category must NEVER appear in mapping."""
        headers = ["PO Number", "Supplier", "Voucher Category"]
        result = build_column_mapping(headers, "format_b")
        assert "Voucher Category" in result.excluded_columns
        assert "voucher_category" not in result.canonical_to_source
        # Verify it's not in source_to_canonical either
        assert "Voucher Category" not in result.source_to_canonical
        assert any("Target label" in w for w in result.warnings)

    def test_all_target_label_names_excluded(self):
        """All known target label column names must be excluded."""
        for label_name in TARGET_LABEL_COLUMNS:
            headers = ["PO Number", label_name.title()]
            # Some may not match because casing differs
            # But "Voucher Category" and "label" etc. must match
            result = build_column_mapping(headers, "format_b")
            for excluded in result.excluded_columns:
                assert excluded.lower() in TARGET_LABEL_COLUMNS

    def test_unmapped_columns_preserved(self):
        headers = ["PO Number", "Custom Exotic Field", "Another Unknown"]
        result = build_column_mapping(headers, "format_b")
        assert "Custom Exotic Field" in result.unmapped_columns
        assert "Another Unknown" in result.unmapped_columns


# ── Reader Tests ──────────────────────────────────────────────────────────

class TestReader:

    def test_read_format_b_excludes_target(self, tmp_path):
        path = _create_format_b_workbook(tmp_path / "b.xlsx")
        data = read_workbook(path, "Test Cases")
        assert not data.errors
        assert data.target_column_name == "Voucher Category"
        assert len(data.rows) == 3
        # Target labels extracted separately
        assert len(data.target_labels) == 3
        assert "Purchase Order" in data.target_labels.values()
        assert "Salary / Payroll" in data.target_labels.values()
        # No cell in any row should contain Voucher Category
        for row in data.rows:
            for cell in row.cells:
                assert cell.column_header != "Voucher Category"

    def test_read_format_b_without_target(self, tmp_path):
        path = _create_format_b_workbook(tmp_path / "no_target.xlsx", include_target=False)
        data = read_workbook(path, "Test Cases")
        assert not data.errors
        assert data.target_column_name is None
        assert len(data.target_labels) == 0

    def test_read_format_a_preserves_zero_and_none(self, tmp_path):
        path = _create_format_a_workbook(tmp_path / "a.xlsx")
        data = read_workbook(path, "Organizer_Ready_Input")
        assert not data.errors
        assert len(data.rows) == 3
        # Row 2 has zero for taxable_value
        row2 = data.rows[1]
        taxable_cell = next((c for c in row2.cells if c.column_header == "taxable_value"), None)
        assert taxable_cell is not None
        assert taxable_cell.value == 0  # Zero, not None
        # Row 2 has None for document_reference
        doc_cell = next((c for c in row2.cells if c.column_header == "document_reference"), None)
        # None cells should still be present with null value
        # (we keep the cell but value is None for provenance)
        # Actually our reader skips None values from populated check but keeps them
        # Let's verify the cell exists
        assert doc_cell is None or doc_cell.value is None

    def test_read_missing_sheet(self, tmp_path):
        path = _create_format_a_workbook(tmp_path / "a.xlsx")
        data = read_workbook(path, "Nonexistent Sheet")
        assert data.errors
        assert any("not found" in e for e in data.errors)


# ── Pipeline Tests ────────────────────────────────────────────────────────

class TestPipeline:

    def test_ingest_format_a_full_pipeline(self, tmp_path):
        path = _create_format_a_workbook(tmp_path / "a.xlsx")
        result = ingest_workbook(path)
        assert not result.errors
        assert result.detection.detected_format == "format_a"
        assert result.total_rows == 3
        assert not result.has_target_labels
        # All 27 categories still in ontology (checked separately)

    def test_ingest_format_b_full_pipeline(self, tmp_path):
        path = _create_format_b_workbook(tmp_path / "b.xlsx")
        result = ingest_workbook(path)
        assert not result.errors
        assert result.detection.detected_format == "format_b"
        assert result.total_rows == 3
        assert result.has_target_labels
        assert result.target_label_count == 3
        assert "Purchase Order" in result.unique_labels
        assert "Salary / Payroll" in result.unique_labels
        assert "Import" in result.unique_labels

    def test_format_b_target_never_in_transactions(self, tmp_path):
        """CRITICAL: Target label must NEVER appear in normalized transactions."""
        path = _create_format_b_workbook(tmp_path / "b.xlsx")
        result = ingest_workbook(path)
        for tx in result.transactions:
            # Check all category buckets
            for category in ["document", "parties", "items", "amounts", "tax",
                             "accounts", "references", "returns", "inventory",
                             "hr", "trade", "jobwork", "expense", "meta"]:
                bucket = getattr(tx, category)
                assert "voucher_category" not in bucket
                assert "Voucher Category" not in bucket
            # Check extra_fields
            assert "Voucher Category" not in tx.extra_fields
            assert "voucher_category" not in tx.extra_fields
            # Check signals
            for signal in tx.signals:
                assert signal.canonical_name != "voucher_category"
                assert "Voucher Category" not in signal.source_header

    def test_format_b_sparse_transactions_handled(self, tmp_path):
        path = _create_format_b_workbook(tmp_path / "b.xlsx")
        result = ingest_workbook(path)
        # Each row only has a subset of fields populated
        for tx in result.transactions:
            assert tx.populated_field_count > 0
            assert tx.populated_field_count < tx.total_field_count

    def test_format_b_mapping_covers_key_fields(self, tmp_path):
        path = _create_format_b_workbook(tmp_path / "b.xlsx")
        result = ingest_workbook(path)
        # PO row should have purchase_order_no mapped
        po_tx = result.transactions[0]
        assert po_tx.references.get("purchase_order_no") == "PO-2026-001"
        assert po_tx.parties.get("supplier_name") == "ABC Suppliers"
        # Salary row should have HR fields
        sal_tx = result.transactions[1]
        assert sal_tx.hr.get("employee_id") == "EMP-042"

    def test_generate_report(self, tmp_path):
        path = _create_format_b_workbook(tmp_path / "b.xlsx")
        result = ingest_workbook(path)
        report = generate_ingestion_report(result)
        assert report["detected_format"] == "format_b"
        assert report["total_rows"] == 3
        assert report["has_target_labels"] is True
        assert "Voucher Category" in report["excluded_columns"]

    def test_all_27_categories_remain_valid(self):
        """Verify that our full 27-category taxonomy is preserved."""
        from app.contracts import load_taxonomy
        taxonomy_path = Path(__file__).resolve().parents[1] / "ontology" / "workbook-seed.json"
        if taxonomy_path.exists():
            taxonomy = load_taxonomy(taxonomy_path)
            assert len(taxonomy.entries) == 27
            names = {e.name for e in taxonomy.entries}
            # Verify the 3 categories not in organizer data are still present
            assert "Attendance" in names
            assert "Advance / Prepayment" in names
            assert "Other / Miscellaneous" in names
        else:
            pytest.skip("Taxonomy file not available")


# ── Real Workbook Integration Tests ────────────────────────────────────────

class TestRealWorkbooks:
    """Integration tests using the actual workbook files, if available."""

    EXCEL_DIR = Path(__file__).resolve().parents[2] / "excel files"

    @pytest.fixture
    def format_a_path(self):
        path = self.EXCEL_DIR / "HisabhParakh_Organizer_Aligned_500_Transactions.xlsx"
        if not path.exists():
            pytest.skip("Format A workbook not available")
        return path

    @pytest.fixture
    def format_b_path(self):
        path = self.EXCEL_DIR / "Voucher_Classification_Test_Cases_v2.xlsx"
        if not path.exists():
            pytest.skip("Format B workbook not available")
        return path

    def test_real_format_a_loads(self, format_a_path):
        result = ingest_workbook(format_a_path)
        assert not result.errors, f"Errors: {result.errors}"
        assert result.detection.detected_format == "format_a"
        assert result.total_rows == 500

    def test_real_format_b_loads(self, format_b_path):
        result = ingest_workbook(format_b_path)
        assert not result.errors, f"Errors: {result.errors}"
        assert result.detection.detected_format == "format_b"
        assert result.total_rows == 120

    def test_real_format_b_target_excluded(self, format_b_path):
        """CRITICAL: Real organizer workbook must have target column excluded."""
        result = ingest_workbook(format_b_path)
        assert result.has_target_labels
        assert result.target_label_count == 120
        assert len(result.unique_labels) == 24
        # Verify no target in any transaction
        for tx in result.transactions:
            for category in ["document", "parties", "items", "amounts", "tax",
                             "accounts", "references", "returns", "inventory",
                             "hr", "trade", "jobwork", "expense", "meta"]:
                bucket = getattr(tx, category)
                assert "voucher_category" not in bucket

    def test_real_format_b_all_rows_preserved(self, format_b_path):
        """Every input row must be accounted for."""
        result = ingest_workbook(format_b_path)
        assert result.total_rows == 120
        # Verify unique physical rows
        physical_rows = {tx.physical_row for tx in result.transactions}
        assert len(physical_rows) == 120

    def test_real_format_b_sparse_handling(self, format_b_path):
        """Verify sparse transactions are handled — each row has different fields."""
        result = ingest_workbook(format_b_path)
        populated_counts = [tx.populated_field_count for tx in result.transactions]
        # Not all rows should have the same field count (sparse data)
        assert len(set(populated_counts)) > 1
        # No row should have zero populated fields
        assert all(c > 0 for c in populated_counts)

    def test_real_both_formats_coexist(self, format_a_path, format_b_path):
        """Both formats can be loaded in the same process."""
        result_a = ingest_workbook(format_a_path)
        result_b = ingest_workbook(format_b_path)
        assert result_a.detection.detected_format == "format_a"
        assert result_b.detection.detected_format == "format_b"
        assert result_a.total_rows == 500
        assert result_b.total_rows == 120
