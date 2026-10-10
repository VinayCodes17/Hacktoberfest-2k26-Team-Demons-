"""Column mapping: map workbook headers to canonical transaction fields.

Supports both Format A (snake_case, old synthetic) and Format B (human-readable,
organizer test cases). Unknown fields are preserved in metadata rather than dropped.

CRITICAL: The target label column (Voucher Category) is NEVER mapped to any
canonical field. It is explicitly excluded and tracked separately.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ingestion.profiler import TARGET_LABEL_COLUMNS
from app.ingestion.schema_detector import FormatType

# ── Canonical field categories ─────────────────────────────────────────────
# These are the normalized field names used in CanonicalTransaction.
# Grouped by semantic category for clarity.

CANONICAL_DOCUMENT_FIELDS = {
    "document_reference",
    "document_date",
    "document_status",
    "invoice_number",
    "invoice_date",
    "original_invoice_number",
    "narration",
    "transaction_date",
}

CANONICAL_PARTY_FIELDS = {
    "seller_name",
    "seller_id",
    "seller_state",
    "seller_country",
    "supplier_name",
    "buyer_name",
    "buyer_id",
    "buyer_state",
    "buyer_country",
    "customer_name",
    "counterparty_role",
    "counterparty_relationship",
}

CANONICAL_ITEM_FIELDS = {
    "item_code",
    "item_description",
    "item_category",
    "hsn_sac",
    "unit_of_measure",
    "quantity",
    "unit_price",
    "ordered_quantity",
    "received_quantity",
    "dispatched_quantity",
}

CANONICAL_AMOUNT_FIELDS = {
    "taxable_value",
    "discount_amount",
    "freight_amount",
    "invoice_total",
    "amount_paid",
    "amount_received",
    "outstanding_amount",
    "basic_salary",
    "allowances",
    "deductions",
    "gross_pay",
    "net_pay",
    "transfer_amount",
}

CANONICAL_TAX_FIELDS = {
    "cgst_rate_pct",
    "sgst_rate_pct",
    "igst_rate_pct",
    "cgst_amount",
    "sgst_amount",
    "igst_amount",
    "total_tax_amount",
    "customs_duty",
    "import_gst",
}

CANONICAL_ACCOUNT_FIELDS = {
    "from_account",
    "to_account",
    "from_account_owner",
    "to_account_owner",
    "debit_ledger",
    "credit_ledger",
    "bank_name",
    "bank_reference",
    "money_direction",
    "payment_mode",
    "payment_status",
    "payment_reference",
    "payment_due_date",
    "bank_posted",
}

CANONICAL_REFERENCE_FIELDS = {
    "purchase_order_no",
    "sales_order_no",
    "receipt_note_no",
    "delivery_note_no",
    "challan_no",
    "tracking_no",
    "debit_note_no",
    "credit_note_no",
    "order_fulfilment_status",
}

CANONICAL_RETURN_FIELDS = {
    "return_reason",
    "returned_quantity",
    "rejected_quantity",
}

CANONICAL_INVENTORY_FIELDS = {
    "stock_direction",
    "warehouse_from",
    "warehouse_to",
    "stock_book_qty",
    "stock_counted_qty",
    "stock_difference",
    "quality_status",
    "inventory_posted",
}

CANONICAL_HR_FIELDS = {
    "employee_id",
    "employee_name",
    "pay_period",
    "attendance_type",
    "days_present",
    "days_absent",
    "overtime_hours",
}

CANONICAL_TRADE_FIELDS = {
    "foreign_trade_direction",
    "origin_country",
    "destination_country",
    "foreign_counterparty",
    "port_of_loading",
    "port_of_discharge",
    "bill_of_entry_no",
    "shipping_bill_no",
    "incoterm",
    "currency",
    "exchange_rate_inr",
}

CANONICAL_JOBWORK_FIELDS = {
    "job_work_order_no",
    "job_work_role",
    "job_work_process",
}

CANONICAL_EXPENSE_FIELDS = {
    "expense_head",
    "advance_reference",
}

CANONICAL_META_FIELDS = {
    "transaction_id",
    "record_origin",
    "input_schema_variant",
    "invoice_posted",
}

ALL_CANONICAL_FIELDS = (
    CANONICAL_DOCUMENT_FIELDS
    | CANONICAL_PARTY_FIELDS
    | CANONICAL_ITEM_FIELDS
    | CANONICAL_AMOUNT_FIELDS
    | CANONICAL_TAX_FIELDS
    | CANONICAL_ACCOUNT_FIELDS
    | CANONICAL_REFERENCE_FIELDS
    | CANONICAL_RETURN_FIELDS
    | CANONICAL_INVENTORY_FIELDS
    | CANONICAL_HR_FIELDS
    | CANONICAL_TRADE_FIELDS
    | CANONICAL_JOBWORK_FIELDS
    | CANONICAL_EXPENSE_FIELDS
    | CANONICAL_META_FIELDS
)


# ── Format B → canonical mapping ──────────────────────────────────────────
# Maps organizer human-readable column names to canonical field names.
# Ambiguous or context-dependent mappings are flagged with comments.

FORMAT_B_COLUMN_MAP: dict[str, str] = {
    # Document fields
    "Document Number": "document_reference",
    "Document Date": "document_date",
    "Transaction Date": "transaction_date",
    # Party fields
    "Supplier": "supplier_name",
    "Customer": "customer_name",
    "Vendor Name": "seller_name",
    "Company": "buyer_name",
    "Ordering Company": "buyer_name",  # PO context
    "Receiving Company": "buyer_name",  # GRN context
    "Payer Organization": "from_account_owner",
    "Payee Organization": "to_account_owner",
    "Receiving Organization": "buyer_name",  # Receipt context
    "Paying Organization": "from_account_owner",  # Receipt context
    "Exporter": "seller_name",  # Export context
    "Importer": "buyer_name",  # Import context
    "Selling Company": "seller_name",  # SO context
    "Principal": "buyer_name",  # Job work context
    "Contractor": "foreign_counterparty",
    "Processor": "foreign_counterparty",  # JWOO context
    "Subcontractor": "foreign_counterparty",  # JWIO context
    # Item fields
    "Item": "item_description",
    "Product": "item_description",  # Return context
    "Item Received": "item_description",  # GRN context
    "Item Rejected": "item_description",  # Rejection context
    "Item Dispatched": "item_description",  # DN context
    "Export Item": "item_description",  # Export context
    "Import Item": "item_description",  # Import context
    "Material": "item_description",  # Job work context
    "Material Description": "item_description",  # Material In context
    "Item Name": "item_description",  # Stock journal context
    "Quantity Required": "ordered_quantity",
    "Quantity Received": "received_quantity",
    "Quantity Shipped": "dispatched_quantity",
    "Quantity Rejected": "rejected_quantity",
    "Units Returned": "returned_quantity",
    "Units Exported": "dispatched_quantity",  # Export context
    "Units Imported": "received_quantity",  # Import context
    "Quantity": "quantity",
    "Quantity Sent": "dispatched_quantity",  # JWIO context
    "Quantity Ordered": "ordered_quantity",  # SO context
    "Units": "quantity",  # Return context
    "Adjustment Qty": "stock_difference",
    # Amount fields — caution: context-dependent
    "Unit Rate": "unit_price",
    "Total Value": "invoice_total",
    "Base Amount": "taxable_value",  # CAUTION: may not always be taxable value
    "Tax Amount": "total_tax_amount",
    "Other Charges": "freight_amount",
    "Transport Cost": "freight_amount",
    "Freight Charges": "freight_amount",  # Export context
    "Payment Amount": "amount_paid",
    "Transfer Amount": "transfer_amount",
    "Gross Salary": "gross_pay",
    "Net Payable": "net_pay",
    "Received Amount": "amount_received",
    "Free on Board Value": "taxable_value",  # Export FOB
    "Cost Insurance Freight": "taxable_value",  # Import CIF
    "Customs Duty": "customs_duty",
    "Import GST": "import_gst",
    "Amount": "taxable_value",  # Journal context
    "Amount Claimed": "taxable_value",  # Expense context
    "Service Charge": "unit_price",  # JWOO context
    "Processing Rate": "unit_price",  # JWIO context
    "Unit Cost": "unit_price",  # Stock adj context
    "Export Incentive": "discount_amount",  # Export incentive mapped here tentatively
    # Tax fields
    "Dearness Allowance": "allowances",
    "Other Benefits": "allowances",
    "Professional Tax": "deductions",
    "Income Tax Deduction": "deductions",
    # Account fields
    "Debit Side": "debit_ledger",
    "Credit Side": "credit_ledger",
    "Source Account": "from_account",
    "Destination Account": "to_account",
    "Mode of Payment": "payment_mode",
    "Payment Type": "payment_mode",
    "Payment Method": "payment_mode",  # Receipt context
    # Reference fields
    "PO Number": "purchase_order_no",
    "SO Number": "sales_order_no",
    "GRN Number": "receipt_note_no",
    "Delivery Challan No": "delivery_note_no",
    "Rejection Note No": "debit_note_no",
    "PO Reference": "purchase_order_no",  # GRN context
    "PO Ref": "purchase_order_no",  # Export context
    "Reference PO": "purchase_order_no",  # Material in context
    "SO Reference": "sales_order_no",  # DN context
    "DN Reference": "delivery_note_no",  # Rejection context
    "GRN Reference": "receipt_note_no",  # Import context
    "Original Doc Ref": "original_invoice_number",
    "Original Invoice Ref": "original_invoice_number",
    "Against Invoice": "original_invoice_number",  # Payment context
    "Transaction Ref": "payment_reference",
    "Reference Number": "payment_reference",  # Payment context
    "Export Invoice No": "invoice_number",  # Export context
    "Import Bill No": "bill_of_entry_no",
    "Consignment Invoice": "invoice_number",  # Import context
    "Outward Job Work No": "job_work_order_no",
    "Inward Job Work No": "job_work_order_no",
    "JWOO Ref": "job_work_order_no",  # JWOO context
    "JWIO Ref": "job_work_order_no",  # JWIO context
    "Contra ID": "document_reference",  # Contra context
    "Payment ID": "document_reference",  # Payment context
    "Receipt ID": "document_reference",  # Receipt context
    "Journal ID": "document_reference",  # Journal context
    "Expense Claim No": "document_reference",  # Expense context
    "Stock Adj ID": "document_reference",  # Stock journal context
    "Stock Count ID": "document_reference",  # Physical stock context
    # Date fields
    "PO Date": "document_date",
    "Rejection Date": "document_date",  # Rejection context
    "Receipt Date": "document_date",  # GRN context
    "Date of Receipt": "document_date",  # Material in context
    "Dispatch Date": "document_date",  # DN context
    "Payment Date": "document_date",  # Payment context
    "Order Date": "document_date",  # JWOO context
    "SO Date": "document_date",  # SO context
    "Entry Date": "document_date",  # Journal context
    "Claim Date": "document_date",  # Expense context
    "Adjustment Date": "document_date",  # Stock adj context
    "Count Date": "document_date",  # Physical stock context
    "Date of Dispatch": "document_date",  # JWIO context
    # Return / rejection fields
    "Reason for Return": "return_reason",
    "Rejection Reason": "return_reason",
    "Reason": "return_reason",  # Stock adj context
    # Inventory fields
    "Storage Location": "warehouse_to",
    "Storage": "warehouse_to",  # Material in context
    "Storage Facility": "warehouse_from",  # Stock adj context
    "Storage Area": "warehouse_from",  # Physical stock context
    "Book Quantity": "stock_book_qty",
    "Counted Quantity": "stock_counted_qty",
    "Discrepancy": "stock_difference",
    "Quality Status": "quality_status",
    "Variance Status": "quality_status",  # Physical stock context
    # Trade fields
    "Currency Code": "currency",
    "Payment Currency": "currency",  # Export context
    "Original Currency": "currency",  # Import context
    "Destination Country": "destination_country",
    "Originating Country": "origin_country",
    "Bank IFSC Code": "bank_reference",
    "Bank Details": "bank_reference",  # Receipt context
    # HR fields
    "Employee Code": "employee_id",
    "Employee Full Name": "employee_name",
    "Payroll Period": "pay_period",
    # Delivery / tracking
    "Promised Delivery": "payment_due_date",  # PO promised date
    "Expected Arrival": "payment_due_date",  # DN expected arrival
    "Delivery Ref": "delivery_note_no",  # Return context
    "Delivery Address": "warehouse_to",  # DN context
    "Courier/Transport": "tracking_no",
    "Completion Due": "payment_due_date",  # JWOO context
    # Context / narration
    "Terms": "narration",
    "Purpose": "narration",  # Material in context
    "Transfer Purpose": "narration",  # Contra context
    "Transaction Details": "narration",  # Payment context
    "Agreement Terms": "narration",  # JWOO context
    "Payment Terms": "narration",  # SO context
    "Narration": "narration",  # Journal context
    "Description": "narration",  # Expense context
    "Notes": "narration",  # Stock adj context
    "Receipt Nature": "narration",  # Receipt context
    "Journal Type": "narration",  # Journal context
    # Misc
    "Authorized By": "narration",
    "Inspected By": "narration",
    "Approved By": "narration",
    "Adjusted By": "narration",
    "Counted By": "narration",
    "Supporting Doc": "narration",
    "Status": "document_status",
    "Expense Type": "expense_head",
    "Vendor/Provider": "seller_name",
    "Department": "narration",
    "Buyer Invoice": "invoice_number",  # Export buyer invoice
}

# Format A columns are already in canonical form (snake_case).
# Build identity mapping for them.
FORMAT_A_COLUMN_MAP: dict[str, str] = {field: field for field in ALL_CANONICAL_FIELDS}


@dataclass
class ColumnMappingResult:
    """Result of mapping workbook columns to canonical fields."""

    format_type: FormatType
    canonical_to_source: dict[str, str]  # canonical_field -> source_column
    source_to_canonical: dict[str, str]  # source_column -> canonical_field
    unmapped_columns: list[str]  # source columns with no canonical mapping
    excluded_columns: list[str]  # target/answer columns excluded
    ambiguous_mappings: list[str]  # warnings about context-dependent mappings
    warnings: list[str]


def build_column_mapping(
    headers: list[str],
    format_type: FormatType,
    user_mapping_overrides: dict[str, str] | None = None,
) -> ColumnMappingResult:
    """Build canonical column mapping for a list of source headers.

    For Format A (old synthetic), columns are already canonical (snake_case).
    For Format B (organizer), maps human-readable names to canonical fields.
    For unknown formats, attempts best-effort mapping via Format B table.

    CRITICAL: Target label columns are always excluded and never mapped.
    """
    canonical_to_source: dict[str, str] = {}
    source_to_canonical: dict[str, str] = {}
    unmapped: list[str] = []
    excluded: list[str] = []
    ambiguous: list[str] = []
    warnings: list[str] = []
    groups: dict[str, list[str]] = {}
    seen: set[str] = set()
    user_mapping = user_mapping_overrides or {}
    aliases = {key.replace("_", " ").casefold(): value for key, value in FORMAT_B_COLUMN_MAP.items()}
    aliases.update(
        {
            "seller supplier": "seller_name",
            "buyer customer": "buyer_name",
            "seller tax id": "seller_id",
            "buyer tax id": "buyer_id",
            "record id": "transaction_id",
            "total amount": "invoice_total",
            "return reference": "original_invoice_number",
        }
    )
    for header in headers:
        clean = header.strip()
        if not clean:
            continue
        if clean.lower() in TARGET_LABEL_COLUMNS:
            excluded.append(clean)
            continue
        if clean in seen:
            ambiguous.append(f"Duplicate source header '{clean}'; use distinct column names.")
            continue
        seen.add(clean)
        canonical = user_mapping.get(clean)
        if canonical is None:
            canonical_key = clean.casefold()
            canonical = (
                canonical_key
                if canonical_key in ALL_CANONICAL_FIELDS
                else aliases.get(clean.replace("_", " ").casefold())
            )
        if canonical not in ALL_CANONICAL_FIELDS:
            unmapped.append(clean)
            if clean in user_mapping:
                ambiguous.append(f"Invalid mapping for '{clean}': choose a supported transaction field.")
            continue
        source_to_canonical[clean] = canonical
        groups.setdefault(canonical, []).append(clean)
    for canonical, sources in groups.items():
        canonical_to_source[canonical] = " | ".join(sources)
    shared = sum(len(sources) > 1 for sources in groups.values())
    if shared:
        warnings.append(
            f"{shared} fields have multiple source columns. Populated columns are resolved per row; simultaneous values retain source-qualified evidence and differing values require review."
        )
    if excluded:
        warnings.append(
            f"Target label / answer columns excluded from classification input (blank values are allowed): {excluded}."
        )
    return ColumnMappingResult(
        format_type=format_type,
        canonical_to_source=canonical_to_source,
        source_to_canonical=source_to_canonical,
        unmapped_columns=unmapped,
        excluded_columns=excluded,
        ambiguous_mappings=ambiguous,
        warnings=warnings,
    )
