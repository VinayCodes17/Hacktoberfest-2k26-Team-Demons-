"""Tests for the normalization module.

Tests verify Decimal handling, date parsing, missing/zero/false distinction,
cell provenance tracking, and sparse transaction context building.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from app.ingestion.column_mapper import build_column_mapping
from app.ingestion.reader import RawCell, RawRow
from app.normalization.normalizer import (
    NormalizedTransaction,
    _safe_date_str,
    _safe_decimal,
    _safe_string,
    build_prompt_context,
    normalize_row,
)

# ── Safe conversion tests ─────────────────────────────────────────────────

class TestSafeDecimal:

    def test_integer_conversion(self):
        val, warn = _safe_decimal(100, "A1")
        assert val == Decimal("100")
        assert warn is None

    def test_float_conversion(self):
        val, warn = _safe_decimal(99.95, "A1")
        assert val == Decimal("99.95")

    def test_string_conversion(self):
        val, warn = _safe_decimal("1,250.50", "A1")
        assert val == Decimal("1250.50")

    def test_currency_symbol_stripped(self):
        val, warn = _safe_decimal("₹5,000", "A1")
        assert val == Decimal("5000")

    def test_none_returns_none(self):
        val, warn = _safe_decimal(None, "A1")
        assert val is None

    def test_zero_is_zero_not_none(self):
        val, warn = _safe_decimal(0, "A1")
        assert val == Decimal("0")
        assert val is not None

    def test_boolean_returns_warning(self):
        val, warn = _safe_decimal(False, "A1")
        assert val is None
        assert warn is not None

    def test_empty_string_returns_none(self):
        val, warn = _safe_decimal("", "A1")
        assert val is None

    def test_dash_returns_none(self):
        val, warn = _safe_decimal("-", "A1")
        assert val is None

    def test_unparseable_returns_warning(self):
        val, warn = _safe_decimal("not a number", "A1")
        assert val is None
        assert warn is not None


class TestSafeDateStr:

    def test_datetime_object(self):
        val, warn = _safe_date_str(datetime(2026, 3, 15, 10, 30), "A1")
        assert val == "2026-03-15"

    def test_date_object(self):
        val, warn = _safe_date_str(date(2026, 3, 15), "A1")
        assert val == "2026-03-15"

    def test_iso_string(self):
        val, warn = _safe_date_str("2026-03-15", "A1")
        assert val == "2026-03-15"

    def test_none_returns_none(self):
        val, warn = _safe_date_str(None, "A1")
        assert val is None

    def test_empty_returns_none(self):
        val, warn = _safe_date_str("", "A1")
        assert val is None


class TestSafeString:

    def test_string_preserved(self):
        assert _safe_string("Hello") == "Hello"

    def test_none_preserved(self):
        assert _safe_string(None) is None

    def test_empty_becomes_none(self):
        assert _safe_string("") is None

    def test_whitespace_becomes_none(self):
        assert _safe_string("   ") is None

    def test_boolean_to_string(self):
        assert _safe_string(False) == "False"
        assert _safe_string(True) == "True"

    def test_number_to_string(self):
        assert _safe_string(42) == "42"


# ── Normalization tests ───────────────────────────────────────────────────

class TestNormalization:

    def _make_row(self, cells_data: list[tuple[str, str, str, object]], 
                  sheet: str = "Test", physical_row: int = 2, 
                  target_label: str | None = None) -> RawRow:
        """Helper to create a RawRow from (coordinate, header, type, value) tuples."""
        cells = [
            RawCell(coordinate=c, column_header=h, cell_type=t, value=v, is_formula=False)
            for c, h, t, v in cells_data
        ]
        return RawRow(sheet_name=sheet, physical_row=physical_row, 
                      cells=cells, target_label=target_label)

    def test_format_b_purchase_order_normalization(self):
        """Test normalization of a Format B Purchase Order row."""
        mapping = build_column_mapping(
            ["PO Number", "Supplier", "Quantity Required", "Unit Rate", "Total Value"],
            "format_b",
        )
        row = self._make_row([
            ("A2", "PO Number", "s", "PO-001"),
            ("B2", "Supplier", "s", "Steel Corp"),
            ("C2", "Quantity Required", "n", 100),
            ("D2", "Unit Rate", "n", 250.50),
            ("E2", "Total Value", "n", 25050),
        ])
        result = normalize_row(row, mapping, "abc123" * 11, 0)
        assert result.references["purchase_order_no"] == "PO-001"
        assert result.parties["supplier_name"] == "Steel Corp"
        assert result.items["ordered_quantity"] == Decimal("100")
        assert result.items["unit_price"] == Decimal("250.50")
        assert result.amounts["invoice_total"] == Decimal("25050")
        assert result.populated_field_count == 5

    def test_format_b_salary_normalization(self):
        """Test normalization of a Format B Salary row."""
        mapping = build_column_mapping(
            ["Employee Code", "Employee Full Name", "Gross Salary", 
             "Net Payable", "Debit Side", "Credit Side"],
            "format_b",
        )
        row = self._make_row([
            ("A2", "Employee Code", "s", "EMP-042"),
            ("B2", "Employee Full Name", "s", "Raj Kumar"),
            ("C2", "Gross Salary", "n", 75000),
            ("D2", "Net Payable", "n", 62000),
            ("E2", "Debit Side", "s", "Salary Expense"),
            ("F2", "Credit Side", "s", "Bank A/c"),
        ])
        result = normalize_row(row, mapping, "def456" * 11, 0)
        assert result.hr["employee_id"] == "EMP-042"
        assert result.hr["employee_name"] == "Raj Kumar"
        assert result.amounts["gross_pay"] == Decimal("75000")
        assert result.amounts["net_pay"] == Decimal("62000")
        assert result.accounts["debit_ledger"] == "Salary Expense"
        assert result.accounts["credit_ledger"] == "Bank A/c"

    def test_zero_vs_missing_distinction(self):
        """Zero must remain zero, not become None."""
        mapping = build_column_mapping(
            ["taxable_value", "discount_amount"],
            "format_a",
        )
        row = self._make_row([
            ("A2", "taxable_value", "n", 0),
            ("B2", "discount_amount", "n", None),
        ])
        result = normalize_row(row, mapping, "ghi789" * 11, 0)
        # Zero is preserved
        assert result.amounts.get("taxable_value") == Decimal("0")
        # None/missing is not in amounts
        assert "discount_amount" not in result.amounts

    def test_target_label_preserved_separately(self):
        """Target label stored in transaction but NOT in any data bucket."""
        mapping = build_column_mapping(
            ["PO Number", "Supplier"],
            "format_b",
        )
        row = self._make_row(
            [("A2", "PO Number", "s", "PO-001"), ("B2", "Supplier", "s", "Corp")],
            target_label="Purchase Order",
        )
        result = normalize_row(row, mapping, "jkl012" * 11, 0)
        assert result.target_label == "Purchase Order"
        # Target must not be in any data bucket
        for category in ["document", "parties", "items", "amounts", "tax",
                         "accounts", "references", "returns", "inventory",
                         "hr", "trade", "jobwork", "expense", "meta"]:
            bucket = getattr(result, category)
            assert "voucher_category" not in bucket

    def test_unmapped_fields_in_extra(self):
        """Unknown fields should be preserved in extra_fields."""
        mapping = build_column_mapping(
            ["PO Number", "Exotic Custom Field"],
            "format_b",
        )
        row = self._make_row([
            ("A2", "PO Number", "s", "PO-001"),
            ("B2", "Exotic Custom Field", "s", "custom value"),
        ])
        result = normalize_row(row, mapping, "mno345" * 11, 0)
        assert "Exotic Custom Field" in result.extra_fields
        assert result.extra_fields["Exotic Custom Field"] == "custom value"


# ── Prompt Context Tests ──────────────────────────────────────────────────

class TestPromptContext:

    def test_context_only_includes_populated_fields(self):
        tx = NormalizedTransaction(
            transaction_id="test",
            source_sheet="Test",
            physical_row=2,
            source_sha256="abc" * 22,
        )
        tx.references["purchase_order_no"] = "PO-001"
        tx.parties["supplier_name"] = "Steel Corp"
        tx.amounts["invoice_total"] = Decimal("25000")
        tx.populated_field_count = 3
        tx.total_field_count = 169

        context = build_prompt_context(tx)
        assert "purchase_order_no" in context
        assert "supplier_name" in context
        assert "invoice_total" in context
        # Should NOT have empty categories
        assert len(context) == 3

    def test_context_does_not_include_target_label(self):
        tx = NormalizedTransaction(
            transaction_id="test",
            source_sheet="Test",
            physical_row=2,
            source_sha256="abc" * 22,
            target_label="Purchase Order",
        )
        tx.references["purchase_order_no"] = "PO-001"
        context = build_prompt_context(tx)
        assert "target_label" not in context
        assert "voucher_category" not in context
        assert "Purchase Order" not in context.values()

    def test_context_converts_decimal_to_string(self):
        tx = NormalizedTransaction(
            transaction_id="test",
            source_sheet="Test",
            physical_row=2,
            source_sha256="abc" * 22,
        )
        tx.amounts["invoice_total"] = Decimal("25000.50")
        context = build_prompt_context(tx)
        assert context["invoice_total"] == "25000.50"
        assert isinstance(context["invoice_total"], str)

    def test_context_max_fields_limit(self):
        tx = NormalizedTransaction(
            transaction_id="test",
            source_sheet="Test",
            physical_row=2,
            source_sha256="abc" * 22,
        )
        # Add many fields
        for i in range(100):
            tx.extra_fields[f"field_{i}"] = f"value_{i}"
        context = build_prompt_context(tx, max_fields=10)
        assert len(context) <= 10
