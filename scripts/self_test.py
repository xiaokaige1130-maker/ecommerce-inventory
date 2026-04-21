import json
import os
import shutil
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
        "item_id": "1",
        "warehouse_id": "1",
        "quantity": "10",
        "unit_cost": "5",
        "source_no": "PO-TEST",
    },
    follow_redirects=True,
)
assert purchase_resp.status_code == 200

sales_resp = client.post(
    "/sales",
    data={
        "customer_id": "2",
        "item_id": "2",
        "warehouse_id": "1",
        "quantity": "2",
        "sale_price": "99",
        "source_no": "SO-TEST",
    },
    follow_redirects=True,
)
assert sales_resp.status_code == 200

order_resp = client.post(
    "/orders",
    data={
        "order_no": "WEB-TEST",
        "platform": "测试平台",
        "shop_name": "测试店铺",
        "customer_id": "2",
        "customer_name": "测试客户",
        "warehouse_id": "1",
        "item_id": "2",
        "quantity": "1",
        "sale_price": "99",
    },
    follow_redirects=True,
)
assert order_resp.status_code == 200
assert client.get("/orders").status_code == 200
for kind in ("items", "orders", "purchase", "stock"):
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
    follow_redirects=True,
)
assert import_resp.status_code == 200
lock_resp = client.post("/warehouse-workbench", data={"action": "lock", "order_id": "1"}, follow_redirects=True)
assert lock_resp.status_code == 200
ship_resp = client.post(
    "/warehouse-workbench",
    data={"action": "ship", "order_id": "1", "logistics_company": "顺丰", "tracking_no": "SF001"},
    follow_redirects=True,
)
assert ship_resp.status_code == 200

pay_resp = client.post(
    "/accounts",
    data={"entry_type": "customer_receive", "partner_id": "2", "amount": "50", "source_no": "PAY-TEST"},
    follow_redirects=True,
)
assert pay_resp.status_code == 200
settlement_resp = client.post(
    "/accounts",
    data={"action": "settlement", "settlement_no": "SET-TEST", "platform": "测试平台", "amount": "100", "commission": "5", "freight": "3", "refund_amount": "2"},
    follow_redirects=True,
)
assert settlement_resp.status_code == 200

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
assert client.get("/stock").status_code == 200
assert client.get("/returns").status_code == 200
assert client.get("/warehouse-workbench").status_code == 200
for kind in ("stock", "accounts", "returns", "purchase", "sales", "orders", "settlements"):
    assert client.get(f"/export/{kind}").status_code == 200
print("Self test passed.")
