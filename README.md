# 小凯哥电商进销存

轻量级中文 Web 进销存系统，面向电商仓库和小团队，覆盖采购、销售、库存、财务、退货全链路管理。

## 功能特性

- **商品管理**：成品货、半成品、物料、包材统一资料管理，支持平台 SKU、默认供应商、采购提前期、安全库存、默认仓库/货位
- **订单中心**：电商订单录入、查询、状态跟踪
- **出库发货**：订单锁库、销售出库、发货扣库存、取消释放库存
- **库存中心**：采购入库、销售出库、退货入库、盘盈盘亏、生产入库、领用出库、锁定库存、可用库存、仓库/货位管理
- **单据管理**：采购单、销售单、订单
- **往来管理**：客户、供应商管理；客户应收、供应商应付、客户收款、供应商付款、平台对账
- **采购建议**：按安全库存、30 天销量、采购提前期自动估算建议采购数
- **BOM 管理**：成品/半成品与物料/包材的组成用量关系
- **售后退货**：待匹配退货人工绑定成品后入库，生成售后记录；对接退货系统 API
- **老板首页看板**：季度销售/退货数据、退货异常、热销品、高退货品、待处理订单、低库存预警
- **Excel 导出**：库存、采购、销售、订单、账目、平台对账、退货
- **角色权限**：老板、仓库、采购、销售、财务、管理员
- **部署方式**：本地运行 / Docker 部署 / Windows 启动脚本

## 技术栈

- **后端**：Flask 3.1
- **数据库**：SQLite
- **前端**：Jinja2 模板 + 原生 CSS
- **Excel 处理**：openpyxl
- **环境配置**：python-dotenv
- **容器化**：Docker + Docker Compose

## 快速开始

### 本地运行

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

访问 http://127.0.0.1:5100 ，默认账号 `admin` / `admin123`

### Docker 部署

```bash
docker compose up -d --build
```

如需对接退货系统 SQLite，将退货系统数据目录挂进容器并配置环境变量：

```env
RETURN_SYSTEM_DATABASE_PATH=/挂载路径/app.db
```

### 环境变量

通过 `.env` 文件或环境变量配置（参考 `.env.example`）：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `APP_NAME` | 应用名称 | 小凯哥电商进销存 |
| `SECRET_KEY` | 会话密钥 | change-me |
| `HOST` | 监听地址 | 0.0.0.0 |
| `PORT` | 监听端口 | 5100 |
| `AUTH_USERNAME` | 管理员账号 | admin |
| `AUTH_PASSWORD` | 管理员密码 | admin123 |
| `RETURN_API_TOKEN` | 退货 API Token | change-me |
| `RETURN_SYSTEM_DATABASE_PATH` | 退货系统数据库路径 | - |

## 项目结构

```
ecommerce-inventory/
├── app/
│   ├── __init__.py           # Flask 应用工厂
│   ├── config.py             # 配置管理（环境变量、路径解析）
│   ├── routes/
│   │   └── main.py           # 路由蓝图（所有业务页面和 API）
│   ├── data/
│   │   ├── database.py       # SQLite 建表、迁移
│   │   └── repositories.py   # 数据访问层
│   ├── templates/            # Jinja2 页面模板
│   │   ├── base.html         # 基础布局
│   │   ├── home.html         # 老板首页看板
│   │   ├── items.html        # 商品管理
│   │   ├── orders.html       # 订单中心
│   │   ├── stock.html        # 库存中心
│   │   ├── sales.html        # 销售管理
│   │   ├── purchase.html     # 采购管理
│   │   ├── warehouse.html    # 仓库管理
│   │   ├── production.html   # 生产管理
│   │   ├── returns.html      # 售后退货
│   │   ├── accounts.html     # 财务对账
│   │   ├── partners.html     # 客户/供应商
│   │   ├── users.html        # 用户管理
│   │   └── ...               # 其他页面
│   └── static/
│       └── style.css         # 全局样式
├── scripts/
│   └── self_test.py          # 自测脚本
├── run.py                    # 启动入口
├── start.bat                 # Windows 启动脚本
├── Dockerfile                # Docker 镜像构建
├── docker-compose.yml        # Docker Compose 编排
└── requirements.txt          # Python 依赖
```

## 退货系统 API

```http
POST /api/returns/inbound
X-API-Token: <RETURN_API_TOKEN>
Content-Type: application/json

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

匹配到成品自动退货入库，匹配不到进入待匹配退货。
