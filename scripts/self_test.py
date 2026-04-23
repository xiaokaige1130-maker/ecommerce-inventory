import json
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path
from io import BytesIO

from openpyxl import Workbook


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / ".test_runtime"
if RUNTIME.exists():
    shutil.rmtree(RUNTIME)
RUNTIME.mkdir()

os.environ["DATABASE_PATH"] = str(RUNTIME / "app.db")
os.environ["EXPORT_DIR"] = str(RUNTIME / "exports")
os.environ["AUTH_USERNAME"] = "admin"
os.environ["AUTH_PASSWORD"] = "admin123"
os.environ["RETURN_API_TOKEN"] = "test-token"

from app import create_app  # noqa: E402


app = create_app()
client = app.test_client()

assert client.get("/login").status_code == 200
evil_login = client.post("/login?next=https://example.com/phish", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
assert evil_login.status_code == 302
assert evil_login.headers["Location"].endswith("/")
resp = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
assert resp.status_code == 200

client.post(
    "/partners",
    data={"partner_type": "supplier", "name": "默认供应商"},
    follow_redirects=True,
)
client.post(
    "/partners",
    data={"partner_type": "customer", "name": "默认客户"},
    follow_redirects=True,
)
edit_partner_resp = client.post(
    "/partners",
    data={"partner_id": "2", "partner_type": "customer", "name": "默认客户", "contact_name": "张三", "phone": "123456"},
    follow_redirects=True,
)
assert edit_partner_resp.status_code == 200
assert client.get("/partners?partner_type=customer&keyword=张三").status_code == 200
client.post(
    "/items",
    data={
        "item_type": "material",
        "item_code": "WL001",
        "item_name": "测试物料",
        "unit": "件",
        "default_warehouse_id": "1",
    },
    follow_redirects=True,
)
edit_item_resp = client.post(
    "/items",
    data={
        "item_id": "2",
        "item_type": "finished",
        "item_code": "CP001",
        "item_name": "测试成品-改",
        "sku": "SKU001",
        "unit": "件",
        "default_warehouse_id": "1",
        "default_location_id": "1",
        "supplier_id": "1",
        "lead_days": "5",
        "sale_price": "109",
        "safety_stock": "6",
        "is_sellable": "1",
    },
    follow_redirects=True,
)
assert edit_item_resp.status_code == 200
assert client.get("/items?keyword=测试成品-改").status_code == 200
client.post(
    "/locations",
    data={"warehouse_id": "1", "location_code": "A-01"},
    follow_redirects=True,
)
client.post(
    "/items",
    data={
        "item_type": "finished",
        "item_code": "CP001",
        "item_name": "测试成品",
        "sku": "SKU001",
        "unit": "件",
        "default_warehouse_id": "1",
        "default_location_id": "1",
        "supplier_id": "1",
        "lead_days": "3",
        "sale_price": "99",
        "safety_stock": "5",
        "is_sellable": "1",
    },
    follow_redirects=True,
)
purchase_resp = client.post(
    "/purchase",
    data={
        "supplier_id": "1",
        "item_id": ["1", "1"],
        "warehouse_id": ["1", "1"],
        "quantity": ["10", "2"],
        "unit_cost": ["5", "6"],
        "source_no": "PO-TEST",
    },
    follow_redirects=True,
)
assert purchase_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    purchase_version = conn.execute("SELECT row_version FROM documents WHERE id = 1").fetchone()[0]
edit_purchase_resp = client.post(
    "/purchase",
    data={
        "document_id": "1",
        "expected_version": str(purchase_version),
        "partner_id": "1",
        "item_id": ["1"],
        "warehouse_id": ["1"],
        "quantity": ["8"],
        "unit_cost": ["5.5"],
        "source_no": "PO-TEST-EDIT",
        "note": "更新采购单",
    },
    follow_redirects=True,
)
assert edit_purchase_resp.status_code == 200
assert client.get("/purchase?keyword=PO-TEST-EDIT").status_code == 200

stock_seed_resp = client.post(
    "/stock",
    data={
        "movement_type": "adjust_in",
        "item_id": "2",
        "warehouse_id": "1",
        "quantity": "5",
        "unit_cost": "60",
        "source_no": "SEED-FINISHED",
    },
    follow_redirects=True,
)
assert stock_seed_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    stock_movement = conn.execute("SELECT id, row_version FROM stock_movements WHERE source_no = 'SEED-FINISHED'").fetchone()
edit_stock_resp = client.post(
    "/stock",
    data={
        "movement_id": str(stock_movement[0]),
        "expected_version": str(stock_movement[1]),
        "expected_stock_snapshot": "",
        "movement_type": "adjust_in",
        "item_id": "2",
        "warehouse_id": "1",
        "quantity": "6",
        "unit_cost": "61",
        "source_no": "SEED-FINISHED-EDIT",
        "note": "更新库存流水",
    },
    follow_redirects=True,
)
assert edit_stock_resp.status_code == 200
overdraw_resp = client.post(
    "/stock",
    data={
        "movement_type": "sale_out",
        "item_id": "2",
        "warehouse_id": "1",
        "quantity": "999",
        "unit_cost": "60",
        "source_no": "OVERDRAW",
    },
    follow_redirects=True,
)
assert overdraw_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    assert conn.execute("SELECT COUNT(*) FROM stock_movements WHERE source_no = 'OVERDRAW'").fetchone()[0] == 0

sales_resp = client.post(
    "/sales",
    data={
        "customer_id": "2",
        "item_id": ["2", "2"],
        "warehouse_id": ["1", "1"],
        "quantity": ["2", "1"],
        "sale_price": ["99", "100"],
        "source_no": "SO-TEST",
    },
    follow_redirects=True,
)
assert sales_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    sales_version = conn.execute("SELECT row_version FROM documents WHERE id = 2").fetchone()[0]
edit_sales_resp = client.post(
    "/sales",
    data={
        "document_id": "2",
        "expected_version": str(sales_version),
        "partner_id": "2",
        "item_id": ["2"],
        "warehouse_id": ["1"],
        "quantity": ["2"],
        "sale_price": ["101"],
        "source_no": "SO-TEST-EDIT",
        "note": "更新销售单",
    },
    follow_redirects=True,
)
assert edit_sales_resp.status_code == 200

order_resp = client.post(
    "/orders",
    data={
        "order_no": "WEB-TEST",
        "platform": "测试平台",
        "shop_name": "测试店铺",
        "customer_id": "2",
        "customer_name": "测试客户",
        "warehouse_id": "1",
        "item_id": ["2", "2"],
        "quantity": ["1", "1"],
        "sale_price": ["99", "98"],
    },
    follow_redirects=True,
)
assert order_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    order_version = conn.execute("SELECT row_version FROM sales_orders WHERE id = 1").fetchone()[0]
edit_order_resp = client.post(
    "/orders",
    data={
        "order_id": "1",
        "expected_version": str(order_version),
        "order_no": "WEB-TEST-EDIT",
        "platform": "测试平台",
        "shop_name": "测试店铺",
        "customer_id": "2",
        "customer_name": "测试客户",
        "warehouse_id": "1",
        "item_id": ["2"],
        "quantity": ["1"],
        "sale_price": ["97"],
        "note": "编辑订单",
    },
    follow_redirects=True,
)
assert edit_order_resp.status_code == 200
assert client.get("/orders").status_code == 200
assert client.get("/orders?status=pending_review&keyword=WEB-TEST-EDIT").status_code == 200
assert client.get("/orders?source_channel=manual&date_from=2026-01-01&date_to=2026-12-31").status_code == 200
for kind in ("items", "orders", "purchase", "stock", "shipments"):
    assert client.get(f"/template/{kind}").status_code == 200

wb = Workbook()
ws = wb.active
ws.append(["平台", "店铺", "订单号", "商品编号或SKU", "商品名称", "数量", "销售单价", "客户姓名", "物流公司", "快递单号", "备注"])
ws.append(["拼多多", "默认店铺", "PDD-IMPORT-1", "SKU001", "测试成品", 1, 88, "导入客户", "中通", "ZT001", "导入测试"])
buf = BytesIO()
wb.save(buf)
buf.seek(0)
import_resp = client.post(
    "/import/orders",
    data={"file": (buf, "orders.xlsx")},
    content_type="multipart/form-data",
    follow_redirects=False,
)
assert import_resp.status_code == 200
assert "导入预检".encode("utf-8") in import_resp.data
preview_token = re.search(rb'name="preview_token" value="([^"]+)"', import_resp.data)
assert preview_token
confirm_resp = client.post(
    "/import/orders",
    data={"confirm_import": "1", "preview_token": preview_token.group(1).decode()},
    follow_redirects=True,
)
assert confirm_resp.status_code == 200
lock_resp = client.post("/warehouse-workbench", data={"action": "lock", "order_id": "1"}, follow_redirects=True)
assert lock_resp.status_code == 200
ship_resp = client.post(
    "/warehouse-workbench",
    data={"action": "ship", "order_id": "1", "logistics_company": "顺丰", "tracking_no": "SF001"},
    follow_redirects=True,
)
assert ship_resp.status_code == 200
cancel_after_ship = client.post("/warehouse-workbench", data={"action": "cancel", "order_id": "1"}, follow_redirects=True)
assert "当前状态不能取消".encode("utf-8") in cancel_after_ship.data
assert client.get("/orders/1").status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    red_order_version = conn.execute("SELECT row_version FROM sales_orders WHERE id = 1").fetchone()[0]
red_order_resp = client.post("/orders/1/action", data={"action": "red_flush", "expected_version": str(red_order_version)}, follow_redirects=True)
assert red_order_resp.status_code == 200

accounts_page = client.get("/accounts")
accounts_snapshot = re.search(rb'name="expected_accounts_snapshot" value="([^"]*)"', accounts_page.data).group(1).decode()
pay_resp = client.post(
    "/accounts",
    data={"entry_type": "customer_receive", "partner_id": "2", "amount": "50", "source_no": "PAY-TEST", "expected_accounts_snapshot": accounts_snapshot},
    follow_redirects=True,
)
assert pay_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    payment_entry = conn.execute("SELECT id, row_version FROM account_entries WHERE source_no = 'PAY-TEST'").fetchone()
edit_pay_resp = client.post(
    "/accounts",
    data={
        "action": "payment",
        "entry_id": str(payment_entry[0]),
        "expected_version": str(payment_entry[1]),
        "expected_accounts_snapshot": "",
        "entry_type": "customer_receive",
        "partner_id": "2",
        "amount": "55",
        "source_no": "PAY-TEST-EDIT",
        "note": "更新收款",
    },
    follow_redirects=True,
)
assert edit_pay_resp.status_code == 200
stale_account_resp = client.post(
    "/accounts",
    data={"entry_type": "customer_receive", "partner_id": "2", "amount": "10", "source_no": "PAY-STALE", "expected_accounts_snapshot": accounts_snapshot},
    follow_redirects=True,
)
assert "账目页面已经有新数据写入".encode("utf-8") in stale_account_resp.data
settlement_resp = client.post(
    "/accounts",
    data={"action": "settlement", "settlement_no": "SET-TEST", "platform": "测试平台", "amount": "100", "commission": "5", "freight": "3", "refund_amount": "2", "expected_accounts_snapshot": ""},
    follow_redirects=True,
)
assert settlement_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    settlement_row = conn.execute("SELECT id, row_version FROM platform_settlements WHERE settlement_no = 'SET-TEST'").fetchone()
edit_settlement_resp = client.post(
    "/accounts",
    data={
        "action": "settlement",
        "settlement_id": str(settlement_row[0]),
        "expected_version": str(settlement_row[1]),
        "expected_accounts_snapshot": "",
        "settlement_no": "SET-TEST-EDIT",
        "platform": "测试平台",
        "amount": "120",
        "commission": "6",
        "freight": "4",
        "refund_amount": "2",
        "settled_at": "2026-04-24",
        "note": "更新平台对账",
    },
    follow_redirects=True,
)
assert edit_settlement_resp.status_code == 200
assert client.get("/purchase?keyword=PO-TEST-EDIT").status_code == 200
assert client.get("/sales?keyword=SO-TEST-EDIT").status_code == 200
assert client.get("/purchase?source_channel=manual&date_from=2026-01-01&date_to=2026-12-31").status_code == 200
assert client.get("/sales?source_channel=manual&date_from=2026-01-01&date_to=2026-12-31").status_code == 200
assert client.get("/stock?movement_type=adjust_in&movement_keyword=SEED-FINISHED&date_from=2026-01-01&date_to=2026-12-31").status_code == 200
assert client.get("/accounts?source_type=payment&keyword=PAY-TEST&date_from=2026-01-01&date_to=2026-12-31").status_code == 200
purchase_detail = client.get("/documents/purchase/1")
assert purchase_detail.status_code == 200
assert "操作日志".encode("utf-8") in purchase_detail.data
sales_detail = client.get("/documents/sale/2")
assert sales_detail.status_code == 200
assert "操作日志".encode("utf-8") in sales_detail.data
assert client.get("/orders?copy_id=1").status_code == 200
assert client.get("/purchase?copy_id=1").status_code == 200
assert client.get("/sales?copy_id=2").status_code == 200
exceptions_page = client.get("/exceptions")
assert exceptions_page.status_code == 200
assert "异常看板".encode("utf-8") in exceptions_page.data

stock_page = client.get("/stock")
stock_snapshot = re.search(rb'name="expected_stock_snapshot" value="([^"]*)"', stock_page.data).group(1).decode()
fresh_stock_resp = client.post(
    "/stock",
    data={
        "movement_type": "adjust_in",
        "item_id": "1",
        "warehouse_id": "1",
        "quantity": "1",
        "unit_cost": "5",
        "source_no": "SNAP-OK",
        "expected_stock_snapshot": stock_snapshot,
    },
    follow_redirects=True,
)
assert fresh_stock_resp.status_code == 200
stale_stock_resp = client.post(
    "/stock",
    data={
        "movement_type": "adjust_in",
        "item_id": "1",
        "warehouse_id": "1",
        "quantity": "1",
        "unit_cost": "5",
        "source_no": "SNAP-STALE",
        "expected_stock_snapshot": stock_snapshot,
    },
    follow_redirects=True,
)
assert "库存页面已有新流水".encode("utf-8") in stale_stock_resp.data
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    edited_stock = conn.execute("SELECT id, row_version FROM stock_movements WHERE source_no = 'SEED-FINISHED-EDIT'").fetchone()
void_stock_resp = client.post(f"/stock/{edited_stock[0]}/action", data={"action": "void", "expected_version": str(edited_stock[1])}, follow_redirects=True)
assert void_stock_resp.status_code == 200

void_order_resp = client.post(
    "/orders",
    data={
        "order_no": "VOID-ORDER",
        "platform": "测试平台",
        "shop_name": "测试店铺",
        "customer_id": "2",
        "customer_name": "测试客户",
        "warehouse_id": "1",
        "item_id": ["2"],
        "quantity": ["1"],
        "sale_price": ["88"],
    },
    follow_redirects=True,
)
assert void_order_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    void_order = conn.execute("SELECT id, row_version FROM sales_orders WHERE order_no = 'VOID-ORDER'").fetchone()
void_action_resp = client.post(f"/orders/{void_order[0]}/action", data={"action": "void", "expected_version": str(void_order[1])}, follow_redirects=True)
assert void_action_resp.status_code == 200

void_purchase_resp = client.post(
    "/purchase",
    data={
        "partner_id": "1",
        "item_id": ["1"],
        "warehouse_id": ["1"],
        "quantity": ["1"],
        "unit_cost": ["5"],
        "source_no": "PO-VOID",
    },
    follow_redirects=True,
)
assert void_purchase_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    void_purchase = conn.execute("SELECT id, row_version FROM documents WHERE document_no = 'PO-VOID'").fetchone()
void_purchase_action = client.post(f"/documents/purchase/{void_purchase[0]}/action", data={"action": "void", "expected_version": str(void_purchase[1])}, follow_redirects=True)
assert void_purchase_action.status_code == 200

red_sales_resp = client.post(
    "/sales",
    data={
        "partner_id": "2",
        "item_id": ["2"],
        "warehouse_id": ["1"],
        "quantity": ["1"],
        "sale_price": ["90"],
        "source_no": "SO-RED",
    },
    follow_redirects=True,
)
assert red_sales_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    red_sale = conn.execute("SELECT id, row_version FROM documents WHERE document_no = 'SO-RED'").fetchone()
red_sale_action = client.post(f"/documents/sale/{red_sale[0]}/action", data={"action": "red_flush", "expected_version": str(red_sale[1])}, follow_redirects=True)
assert red_sale_action.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    edited_payment = conn.execute("SELECT id, row_version FROM account_entries WHERE source_no = 'PAY-TEST-EDIT'").fetchone()
void_payment_resp = client.post(f"/accounts/entries/{edited_payment[0]}/action", data={"action": "void", "expected_version": str(edited_payment[1])}, follow_redirects=True)
assert void_payment_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    edited_settlement = conn.execute("SELECT id, row_version FROM platform_settlements WHERE settlement_no = 'SET-TEST-EDIT'").fetchone()
void_settlement_resp = client.post(f"/accounts/settlements/{edited_settlement[0]}/action", data={"action": "void", "expected_version": str(edited_settlement[1])}, follow_redirects=True)
assert void_settlement_resp.status_code == 200

client.post(
    "/production",
    data={"action": "bom", "finished_item_id": "2", "component_item_id": "1", "quantity": "1"},
    follow_redirects=True,
)
prod_resp = client.post(
    "/production",
    data={"action": "produce", "finished_item_id": "2", "warehouse_id": "1", "quantity": "1", "source_no": "PD-TEST"},
    follow_redirects=True,
)
assert prod_resp.status_code == 200
dup_prod_resp = client.post(
    "/production",
    data={"action": "produce", "finished_item_id": "2", "warehouse_id": "1", "quantity": "1", "source_no": "PD-TEST"},
    follow_redirects=True,
)
assert dup_prod_resp.status_code == 200
with sqlite3.connect(os.environ["DATABASE_PATH"]) as conn:
    assert conn.execute("SELECT COUNT(*) FROM production_orders WHERE production_no = 'PD-TEST'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM stock_movements WHERE source_no = 'PD-TEST'").fetchone()[0] == 2

client.post(
    "/users",
    data={"username": "staff1", "password": "staffpass", "display_name": "员工", "role": "staff"},
    follow_redirects=True,
)
client.get("/logout", follow_redirects=True)
staff_login = client.post("/login", data={"username": "staff1", "password": "staffpass"}, follow_redirects=True)
assert staff_login.status_code == 200
assert "订单中心".encode("utf-8") not in staff_login.data
assert "财务对账".encode("utf-8") not in staff_login.data
assert "首页".encode("utf-8") in staff_login.data
forbidden_accounts = client.get("/accounts", follow_redirects=True)
assert "没有权限".encode("utf-8") in forbidden_accounts.data
client.get("/logout", follow_redirects=True)
resp = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
assert resp.status_code == 200

api_resp = client.post(
    "/api/returns/inbound",
    data=json.dumps({"tracking_no": "YT001", "sku": "SKU001", "product_name": "测试成品", "quantity": 1}),
    content_type="application/json",
    headers={"X-API-Token": "test-token"},
)
assert api_resp.status_code == 200
assert api_resp.get_json()["result"]["status"] == "matched_inbound"
pending_resp = client.post(
    "/api/returns/inbound",
    data=json.dumps({"tracking_no": "YT002", "sku": "UNKNOWN", "product_name": "未知商品", "quantity": 1}),
    content_type="application/json",
    headers={"X-API-Token": "test-token"},
)
assert pending_resp.status_code == 200
assert pending_resp.get_json()["result"]["status"] == "pending_match"
match_resp = client.post("/returns", data={"return_id": "2", "item_id": "2"}, follow_redirects=True)
assert match_resp.status_code == 200
assert client.get("/returns?status=matched_inbound&keyword=YT001&date_from=2026-01-01&date_to=2026-12-31").status_code == 200
assert client.get("/returns/1").status_code == 200
assert client.get("/stock").status_code == 200
assert client.get("/returns").status_code == 200
assert client.get("/warehouse-workbench").status_code == 200
assert client.get("/warehouse-workbench?status=shipped&keyword=WEB-TEST-EDIT&date_from=2026-01-01&date_to=2026-12-31").status_code == 200
batch_lock = client.post("/warehouse-workbench", data={"action": "lock", "order_ids": ["2"]}, follow_redirects=True)
assert batch_lock.status_code == 200

ship_wb = Workbook()
ship_ws = ship_wb.active
ship_ws.append(["订单号", "物流公司", "快递单号"])
ship_ws.append(["PDD-IMPORT-1", "中通", "ZT-IMPORT-1"])
ship_buf = BytesIO()
ship_wb.save(ship_buf)
ship_buf.seek(0)
ship_import_resp = client.post(
    "/warehouse-workbench/import-shipments",
    data={"file": (ship_buf, "shipments.xlsx")},
    content_type="multipart/form-data",
    follow_redirects=True,
)
assert ship_import_resp.status_code == 200
for kind in ("stock", "accounts", "returns", "purchase", "sales", "orders", "settlements"):
    assert client.get(f"/export/{kind}").status_code == 200
print("Self test passed.")
