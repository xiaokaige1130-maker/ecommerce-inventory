# 小凯哥电商进销存

轻量中文 Web 进销存，面向电商仓库和小团队。

## 当前功能

- 成品货、半成品、物料、包材统一资料管理
- 商品资料支持平台 SKU、默认供应商、采购提前期、安全库存、默认仓库/货位
- 订单中心：电商订单录入、查询、状态跟踪
- 出库发货：订单锁库、销售出库、发货扣库存、取消释放库存
- 库存中心：采购入库、销售出库、退货入库、盘盈盘亏、生产入库、领用出库、锁定库存、可用库存、仓库/货位
- 单据：采购单、销售单、订单
- 客户、供应商
- 客户应收、供应商应付、客户收款、供应商付款、平台对账
- 采购建议：按安全库存、30天销量、采购提前期估算建议采购数
- 组成关系：成品/半成品与物料/包材用量
- 待匹配退货人工绑定成品后入库，并生成售后记录
- Excel 导出：库存、采购、销售、订单、账目、平台对账、退货
- 账号角色：老板、仓库、采购、销售、财务、管理员
- 退货系统对接 API
- 老板首页经营看板：季度销售数据、季度退货数据、季度退货异常、卖得好、退得多、待处理订单、低库存
- 售后退货页会自动同步现有退货系统 SQLite 数据
- Windows 启动版
- Docker 部署版

## 页面原则

每个岗位一个页面完成日常操作：

- 老板看 `首页`
- 销售看 `订单中心`
- 仓库看 `出库发货`
- 库存管理员看 `库存中心`
- 采购看 `采购中心`
- 财务看 `财务对账`
- 退货处理看 `售后退货`

页面上半部分是当天常用录入/处理，往下滚动才是查询、汇总、导出。

## 本地运行

```bash
cd /home/hyk/ecommerce-inventory
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

访问：

```text
http://127.0.0.1:5100
admin / admin123
```

## Docker

```bash
cd /home/hyk/ecommerce-inventory
docker compose up -d --build
```

如果 Docker 里也要读取退货系统 SQLite，需要把退货系统数据目录挂进容器，并设置：

```env
RETURN_SYSTEM_DATABASE_PATH=/挂载后的/app.db
```

## 退货系统 API

```http
POST /api/returns/inbound
X-API-Token: change-me
Content-Type: application/json
```

```json
{
  "tracking_no": "快递单号",
  "order_no": "平台订单号",
  "sku": "成品SKU",
  "barcode": "条码",
  "product_name": "商品名称",
  "customer_name": "客户",
  "quantity": 1
}
```

匹配到成品货会自动退货入库；匹配不到会进入待匹配退货。

## 读取退货系统看板数据

默认读取：

```text
/home/hyk/warehouse-management/data/app.db
```

可用环境变量覆盖：

```env
RETURN_SYSTEM_DATABASE_PATH=/path/to/return-system/data/app.db
```
