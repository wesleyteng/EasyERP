# EasyERP Data Model Architecture

## 1. Core Design Principle

EasyERP uses a document-based ERP flow:

Order / POS / Purchase
→ Inventory Movement
→ Accounting Journal Entry

All business transactions must be traceable from source document to inventory movement and accounting entry.

Rules:
- Do not directly modify stock quantity.
- Do not directly modify posted accounting entries.
- All changes must be recorded through transaction documents.
- Historical records should be voided or reversed, not deleted.
- Money fields must use Decimal, never float.

---

## 2. Master Data

### BusinessPartner
Represents customer, supplier, or both.

Fields:
- id
- code
- name
- type: customer / supplier / both
- phone
- email
- address
- is_active
- created_at
- updated_at

### Product
Represents sellable or purchasable item.

Fields:
- id
- sku
- name
- category_id
- unit
- cost_price
- selling_price
- is_inventory_item
- is_active
- created_at
- updated_at

### Warehouse
Represents stock location.

Fields:
- id
- code
- name
- is_active

### Account
Chart of accounts.

Fields:
- id
- account_code
- account_name
- account_type: asset / liability / equity / revenue / expense
- parent_id
- is_active

---

## 3. Order Module

### SalesOrder
Sales document header.

Fields:
- id
- order_no
- order_date
- customer_id
- status: draft / confirmed / completed / void
- subtotal
- tax_amount
- total_amount
- remarks
- created_at
- updated_at
- confirmed_at
- voided_at

### SalesOrderLine
Sales document detail.

Fields:
- id
- sales_order_id
- product_id
- description
- quantity
- unit_price
- discount_amount
- tax_amount
- line_total
- warehouse_id

Rules:
- draft order can be edited.
- confirmed order can generate inventory movement.
- completed order can generate accounting entry.
- voided order cannot be edited.
- Do not delete confirmed or completed orders.

---

## 4. POS Module

### POSTransaction
Fast sales transaction.

Fields:
- id
- pos_no
- transaction_date
- customer_id nullable
- status: draft / paid / void
- payment_status: unpaid / paid / refunded
- subtotal
- tax_amount
- total_amount
- created_at
- voided_at

### POSTransactionLine
Fields:
- id
- pos_transaction_id
- product_id
- quantity
- unit_price
- discount_amount
- tax_amount
- line_total
- warehouse_id

### Payment
Fields:
- id
- source_type: sales_order / pos_transaction
- source_id
- payment_date
- payment_method: cash / bank / card / ewallet
- amount
- reference_no
- status: received / void

Rules:
- paid POS transaction should reduce inventory.
- paid POS transaction may generate journal entry.
- voided POS transaction should create reverse inventory/accounting records.

---

## 5. Inventory Module

### InventoryMovement
Inventory transaction header.

Fields:
- id
- movement_no
- movement_date
- movement_type: sales_out / purchase_in / adjustment / transfer / return_in / return_out
- source_type: sales_order / pos_transaction / purchase_order / manual_adjustment
- source_id
- status: draft / posted / void
- remarks
- created_at
- posted_at
- voided_at

### InventoryMovementLine
Fields:
- id
- movement_id
- product_id
- warehouse_id
- quantity
- unit_cost
- direction: in / out
- source_line_id nullable

### StockBalance
Current stock snapshot.

Fields:
- id
- product_id
- warehouse_id
- quantity_on_hand
- updated_at

Rules:
- StockBalance is derived from posted InventoryMovement.
- Do not manually edit StockBalance except system recalculation tools.
- All stock changes must go through InventoryMovement.
- Posted movement cannot be edited.
- Corrections must use reverse movement or adjustment movement.

---

## 6. Accounting Module

### JournalEntry
Accounting voucher header.

Fields:
- id
- journal_no
- journal_date
- description
- journal_type: general / sales / purchase / payment / adjustment
- source_type nullable
- source_id nullable
- status: draft / posted / void
- currency_code
- currency_rate
- total_debit
- total_credit
- remarks
- created_at
- updated_at
- posted_at
- voided_at

### JournalEntryLine
Accounting voucher detail.

Fields:
- id
- journal_entry_id
- account_id
- account_code
- account_name
- description
- debit_amount
- credit_amount
- partner_id nullable
- product_id nullable
- project_code nullable
- reference_no nullable

Rules:
- debit total must equal credit total.
- amount cannot be negative.
- one line cannot have both debit and credit.
- posted journal entry cannot be edited.
- posted journal entry cannot be hard deleted.
- corrections must use reverse journal entry.

---

## 7. Cross Module Flow

### Sales Order Flow
SalesOrder confirmed
→ InventoryMovement type sales_out
→ JournalEntry type sales

Example accounting:
Debit: Accounts Receivable / Cash
Credit: Sales Revenue
Credit: Tax Payable if applicable

Inventory accounting if enabled:
Debit: Cost of Goods Sold
Credit: Inventory

### POS Flow
POSTransaction paid
→ InventoryMovement type sales_out
→ JournalEntry type sales/payment

Example accounting:
Debit: Cash / Bank / E-wallet
Credit: Sales Revenue
Credit: Tax Payable

### Inventory Adjustment Flow
InventoryAdjustment posted
→ InventoryMovement type adjustment
→ optional JournalEntry type adjustment

### Payment Flow
Payment received
→ JournalEntry type payment

Example accounting:
Debit: Cash / Bank
Credit: Accounts Receivable

---

## 8. Source Tracking Standard

Every generated transaction must include:

- source_type
- source_id
- source_line_id if applicable

Examples:
- JournalEntry.source_type = "sales_order"
- JournalEntry.source_id = SalesOrder.id
- InventoryMovement.source_type = "pos_transaction"
- InventoryMovement.source_id = POSTransaction.id

This allows traceability across modules.

---

## 9. Status Rules

Common statuses:
- draft: editable
- confirmed: business approved, limited editing
- posted: affects inventory/accounting, not editable
- void: cancelled but retained for audit

Rules:
- Do not hard delete business documents after confirmed or posted.
- Use void/reversal records instead.
- Reports should only include posted records unless explicitly requested.

---

## 10. Development Rules for AI

When developing a new feature:
1. Identify the source document.
2. Decide whether it affects inventory.
3. Decide whether it affects accounting.
4. Add source tracking fields.
5. Validate status transition.
6. Do not modify unrelated modules.
7. Keep changes small and staged.
8. Add API validation for business rules.
9. Prefer service layer for business logic.
10. Do not put complex business logic directly inside API routes.