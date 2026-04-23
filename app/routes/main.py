from __future__ import annotations

from functools import wraps
import secrets

from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, session, url_for

from ..data import repositories


main_bp = Blueprint("main", __name__)

ROLE_NAV_ITEMS = {
    "admin": [
        ("main.home", "首页"),
        ("main.items", "商品中心"),
        ("main.orders", "订单中心"),
        ("main.sales", "销售单"),
        ("main.warehouse_workbench", "仓库作业"),
        ("main.stock", "库存中心"),
        ("main.purchase", "采购中心"),
        ("main.production", "生产组装"),
        ("main.partners", "客户供应商"),
        ("main.accounts", "财务对账"),
        ("main.returns", "售后退货"),
        ("main.users", "账号"),
    ],
    "boss": [
        ("main.home", "首页"),
    ],
    "warehouse": [
        ("main.home", "首页"),
        ("main.items", "商品中心"),
        ("main.warehouse_workbench", "仓库作业"),
        ("main.stock", "库存中心"),
        ("main.production", "生产组装"),
        ("main.returns", "售后退货"),
    ],
    "purchase": [
        ("main.home", "首页"),
        ("main.items", "商品中心"),
        ("main.purchase", "采购中心"),
        ("main.partners", "客户供应商"),
    ],
    "sales": [
        ("main.home", "首页"),
        ("main.orders", "订单中心"),
        ("main.sales", "销售单"),
        ("main.partners", "客户供应商"),
    ],
    "finance": [
        ("main.home", "首页"),
        ("main.partners", "客户供应商"),
        ("main.accounts", "财务对账"),
    ],
    "staff": [
        ("main.home", "首页"),
    ],
}

IMPORT_KIND_META = {
    "items": {"label": "商品资料", "endpoint": "main.items"},
    "orders": {"label": "订单", "endpoint": "main.orders"},
    "purchase": {"label": "采购入库", "endpoint": "main.purchase"},
    "stock": {"label": "库存调整", "endpoint": "main.stock"},
}


@main_bp.app_template_filter("item_type_name")
def item_type_name(value: str) -> str:
    return repositories.ITEM_TYPES.get(value, value or "-")


@main_bp.app_template_filter("partner_type_name")
def partner_type_name(value: str) -> str:
    return {"customer": "客户", "supplier": "供应商"}.get(value, value or "-")


@main_bp.app_template_filter("movement_type_name")
def movement_type_name(value: str) -> str:
    return {
        "purchase_in": "采购入库",
        "sale_out": "销售出库",
        "return_in": "退货入库",
        "adjust_in": "盘盈入库",
        "adjust_out": "盘亏出库",
        "production_in": "生产入库",
        "consume_out": "领用出库",
    }.get(value, value or "-")


@main_bp.app_template_filter("role_name")
def role_name(value: str) -> str:
    return {
        "admin": "管理员",
        "boss": "老板",
        "warehouse": "仓库",
        "purchase": "采购",
        "sales": "销售",
        "finance": "财务",
        "staff": "员工",
    }.get(value, value or "-")


@main_bp.app_template_filter("order_status_name")
def order_status_name(value: str) -> str:
    return {
        "pending_review": "待审核",
        "locked": "已锁库",
        "shipped": "已发货",
        "cancelled": "已取消",
    }.get(value, value or "-")


@main_bp.before_app_request
def require_login():
    allowed = {"main.login", "main.api_return_inbound", "static"}
    if request.endpoint in allowed:
        return None
    if not session.get("logged_in"):
        return redirect(url_for("main.login", next=request.path))
    return None


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("main.login", next=request.path))
        return func(*args, **kwargs)

    return wrapper


def roles_required(*roles: str):
    allowed_roles = set(roles)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect(url_for("main.login", next=request.path))
            if session.get("role") not in allowed_roles:
                flash("当前账号没有权限执行该操作", "danger")
                return redirect(url_for("main.home"))
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _safe_next_url(target: str | None) -> str:
    fallback = url_for("main.home")
    if not target:
        return fallback
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return fallback
    if not target.startswith("/"):
        return fallback
    return target


def _import_meta(kind: str) -> dict:
    meta = IMPORT_KIND_META.get(kind)
    if not meta:
        raise ValueError("未知导入类型")
    return meta


def _import_back_url(kind: str) -> str:
    return url_for(_import_meta(kind)["endpoint"])


def _clear_import_draft() -> None:
    draft = session.pop("import_draft", None)
    if draft and draft.get("tmp_path"):
        Path(draft["tmp_path"]).unlink(missing_ok=True)


@main_bp.app_context_processor
def inject_navigation():
    role = session.get("role") or "staff"
    nav_items = ROLE_NAV_ITEMS.get(role, ROLE_NAV_ITEMS["staff"])
    return {"nav_items": nav_items, "current_role": role, "current_role_label": role_name(role)}


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = _safe_next_url(request.args.get("next") or request.form.get("next"))
    if request.method == "POST":
        user = repositories.verify_user(
            current_app.config["DATABASE_PATH"],
            str(request.form.get("username", "")).strip(),
            str(request.form.get("password", "")).strip(),
        )
        if user:
            session["logged_in"] = True
            session["username"] = user["username"]
            session["display_name"] = user.get("display_name") or user["username"]
            session["role"] = user.get("role") or "staff"
            return redirect(next_url)
        flash("用户名或密码错误", "danger")
    return render_template("login.html", next_url=next_url)


@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))


@main_bp.route("/")
@login_required
def home():
    database_path = current_app.config["DATABASE_PATH"]
    role = session.get("role") or "staff"
    dashboard = repositories.owner_dashboard(
        database_path,
        current_app.config["RETURN_SYSTEM_DATABASE_PATH"],
    )
    context = {
        "home_role": role,
        "dashboard": dashboard,
        "stats": dashboard["stats"],
        "movements": repositories.recent_movements(database_path, limit=10),
    }
    if role in {"admin", "boss"}:
        context["home_mode"] = "owner"
    elif role == "warehouse":
        orders = repositories.list_sales_orders(database_path, "", 100)
        stock_rows = repositories.list_stock(database_path)
        returns = repositories.list_return_inbounds(database_path)
        context.update(
            home_mode="warehouse",
            warehouse_focus={
                "pending_review": sum(1 for row in orders if row["status"] == "pending_review"),
                "locked": sum(1 for row in orders if row["status"] == "locked"),
                "pending_returns": sum(1 for row in returns if row["status"] in {"pending_match", "external_abnormal"}),
                "low_stock": sum(1 for row in stock_rows if (row.get("available_qty") or 0) <= (row.get("safety_stock") or 0) and (row.get("safety_stock") or 0) > 0),
            },
            warehouse_orders=orders[:8],
            warehouse_low_stock=[row for row in stock_rows if (row.get("available_qty") or 0) <= (row.get("safety_stock") or 0) and (row.get("safety_stock") or 0) > 0][:8],
            warehouse_returns=returns[:8],
        )
    elif role == "purchase":
        suggestions = repositories.purchase_suggestions(database_path)
        context.update(
            home_mode="purchase",
            purchase_focus={
                "needs_buy": sum(1 for row in suggestions if (row.get("suggest_qty") or 0) > 0),
                "suppliers": len(repositories.list_partners(database_path, "supplier")),
                "recent_docs": len(repositories.list_documents(database_path, "purchase", 10)),
            },
            purchase_suggestions=suggestions[:8],
            purchase_documents=repositories.list_documents(database_path, "purchase", 8),
        )
    elif role == "sales":
        orders = repositories.list_sales_orders(database_path, "", 100)
        context.update(
            home_mode="sales",
            sales_focus={
                "pending_review": sum(1 for row in orders if row["status"] == "pending_review"),
                "locked": sum(1 for row in orders if row["status"] == "locked"),
                "shipped": sum(1 for row in orders if row["status"] == "shipped"),
                "customers": len(repositories.list_partners(database_path, "customer")),
            },
            sales_orders=orders[:8],
            sales_documents=repositories.list_documents(database_path, "sale", 8),
        )
    else:
        context["home_mode"] = "staff"
    return render_template("home.html", **context)


@main_bp.route("/orders/<int:order_id>")
@login_required
@roles_required("admin", "sales", "warehouse")
def order_detail(order_id: int):
    database_path = current_app.config["DATABASE_PATH"]
    order = repositories.get_sales_order(database_path, order_id)
    if not order:
        flash("订单不存在", "danger")
        return redirect(url_for("main.orders"))
    lines = repositories.order_lines(database_path, order_id)
    return render_template("order_detail.html", order=order, lines=lines)


@main_bp.route("/documents/<document_type>/<int:document_id>")
@login_required
@roles_required("admin", "purchase", "sales", "finance")
def document_detail(document_type: str, document_id: int):
    if document_type not in {"purchase", "sale"}:
        flash("单据类型不存在", "danger")
        return redirect(url_for("main.home"))
    database_path = current_app.config["DATABASE_PATH"]
    document = repositories.get_document(database_path, document_id)
    if not document or document["document_type"] != document_type:
        flash("单据不存在", "danger")
        return redirect(url_for("main.purchase" if document_type == "purchase" else "main.sales"))
    lines = repositories.document_lines(database_path, document_id)
    return render_template("document_detail.html", document=document, lines=lines)


@main_bp.route("/template/<kind>")
@login_required
def template(kind: str):
    path = repositories.create_import_template(current_app.config["EXPORT_DIR"], kind)
    return send_file(Path(path), as_attachment=True, download_name=Path(path).name)


@main_bp.route("/import/<kind>", methods=["POST"])
@login_required
def import_data(kind: str):
    back_url = _import_back_url(kind)
    if request.form.get("confirm_import") == "1":
        draft = session.get("import_draft") or {}
        if draft.get("token") != request.form.get("preview_token") or draft.get("kind") != kind:
            flash("导入预检已失效，请重新上传文件", "danger")
            _clear_import_draft()
            return redirect(back_url)
        tmp_path = str(draft.get("tmp_path") or "")
        if not tmp_path or not Path(tmp_path).exists():
            flash("导入临时文件不存在，请重新上传", "danger")
            _clear_import_draft()
            return redirect(back_url)
        try:
            result = repositories.import_excel(
                current_app.config["DATABASE_PATH"],
                tmp_path,
                kind,
                session.get("username", ""),
            )
            flash(f"导入完成：成功 {result['created']} 行，跳过 {result['skipped']} 行", "success" if not result["errors"] else "danger")
            if result["errors"]:
                flash("；".join(result["errors"][:5]), "danger")
        except Exception as exc:
            flash(f"导入失败：{exc}", "danger")
        finally:
            _clear_import_draft()
        return redirect(back_url)

    upload = request.files.get("file")
    if not upload or not upload.filename:
        flash("请选择要导入的 Excel 文件", "danger")
        return redirect(back_url)
    _clear_import_draft()
    suffix = Path(upload.filename).suffix or ".xlsx"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        upload.save(tmp.name)
        tmp_path = tmp.name
    try:
        preview = repositories.import_excel(
            current_app.config["DATABASE_PATH"],
            tmp_path,
            kind,
            session.get("username", ""),
            dry_run=True,
        )
        token = secrets.token_urlsafe(16)
        session["import_draft"] = {"token": token, "kind": kind, "tmp_path": tmp_path}
        return render_template(
            "import_preview.html",
            kind=kind,
            import_label=_import_meta(kind)["label"],
            back_url=back_url,
            preview=preview,
            preview_token=token,
            filename=upload.filename,
        )
    except Exception as exc:
        Path(tmp_path).unlink(missing_ok=True)
        flash(f"导入失败：{exc}", "danger")
        return redirect(back_url)


@main_bp.route("/items", methods=["GET", "POST"])
@login_required
@roles_required("admin", "warehouse", "purchase")
def items():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        try:
            repositories.save_item(database_path, request.form)
            flash("商品资料已保存", "success")
        except Exception as exc:
            flash(f"保存失败：{exc}", "danger")
        return redirect(url_for("main.items", item_type=request.form.get("item_type", "")))
    rows = repositories.list_items(
        database_path,
        item_type=str(request.args.get("item_type", "")).strip(),
        keyword=str(request.args.get("keyword", "")).strip(),
    )
    warehouses = repositories.list_warehouses(database_path)
    return render_template(
        "items.html",
        rows=rows,
        warehouses=warehouses,
        locations=repositories.list_locations(database_path),
        suppliers=repositories.list_partners(database_path, "supplier"),
        item_types=repositories.ITEM_TYPES,
        current_type=str(request.args.get("item_type", "")).strip(),
        keyword=str(request.args.get("keyword", "")).strip(),
    )


@main_bp.route("/stock", methods=["GET", "POST"])
@login_required
@roles_required("admin", "warehouse")
def stock():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        try:
            repositories.create_stock_movement(
                database_path,
                str(request.form.get("movement_type", "")).strip(),
                int(request.form.get("item_id")),
                int(request.form.get("warehouse_id")),
                float(request.form.get("quantity")),
                float(request.form.get("unit_cost") or 0),
                source_type="manual",
                source_no=str(request.form.get("source_no", "")).strip(),
                note=str(request.form.get("note", "")).strip(),
                created_by=session.get("username", ""),
            )
            flash("库存流水已保存", "success")
        except Exception as exc:
            flash(f"保存失败：{exc}", "danger")
        return redirect(url_for("main.stock"))
    return render_template(
        "stock.html",
        stock_rows=repositories.list_stock(database_path),
        movements=repositories.recent_movements(database_path),
        items=repositories.list_items(database_path),
        warehouses=repositories.list_warehouses(database_path),
        locations=repositories.list_locations(database_path),
    )


@main_bp.route("/purchase", methods=["GET", "POST"])
@login_required
@roles_required("admin", "purchase")
def purchase():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        try:
            supplier_id = int(request.form.get("supplier_id"))
            source_no = str(request.form.get("source_no", "")).strip()
            repositories.create_document(
                database_path,
                "purchase",
                partner_id=supplier_id,
                lines=_lines_from_form(request.form, "unit_cost"),
                source_no=source_no,
                note=str(request.form.get("note", "")).strip(),
                created_by=session.get("username", ""),
            )
            flash("采购入库和应付账款已保存", "success")
        except Exception as exc:
            flash(f"保存失败：{exc}", "danger")
        return redirect(url_for("main.purchase"))
    return render_template(
        "purchase.html",
        items=repositories.list_items(database_path),
        warehouses=repositories.list_warehouses(database_path),
        suppliers=repositories.list_partners(database_path, "supplier"),
        movements=repositories.recent_movements(database_path, limit=30),
        documents=repositories.list_documents(database_path, "purchase", str(request.args.get("keyword", "")).strip(), 50),
        suggestions=repositories.purchase_suggestions(database_path),
        keyword=str(request.args.get("keyword", "")).strip(),
    )


@main_bp.route("/sales", methods=["GET", "POST"])
@login_required
@roles_required("admin", "sales")
def sales():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        try:
            customer_id = int(request.form.get("customer_id"))
            source_no = str(request.form.get("source_no", "")).strip()
            repositories.create_document(
                database_path,
                "sale",
                partner_id=customer_id,
                lines=_lines_from_form(request.form, "sale_price"),
                source_no=source_no,
                note=str(request.form.get("note", "")).strip(),
                created_by=session.get("username", ""),
            )
            flash("销售出库和应收账款已保存", "success")
        except Exception as exc:
            flash(f"保存失败：{exc}", "danger")
        return redirect(url_for("main.sales"))
    return render_template(
        "sales.html",
        items=repositories.list_items(database_path, "finished"),
        warehouses=repositories.list_warehouses(database_path),
        customers=repositories.list_partners(database_path, "customer"),
        movements=repositories.recent_movements(database_path, limit=30),
        documents=repositories.list_documents(database_path, "sale", str(request.args.get("keyword", "")).strip(), 50),
        keyword=str(request.args.get("keyword", "")).strip(),
    )


@main_bp.route("/orders", methods=["GET", "POST"])
@login_required
@roles_required("admin", "sales")
def orders():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        try:
            repositories.create_sales_order(database_path, request.form, session.get("username", ""))
            flash("销售订单已保存，仓库可在仓库作业页锁库/发货", "success")
        except Exception as exc:
            flash(f"订单保存失败：{exc}", "danger")
        return redirect(url_for("main.orders"))
    return render_template(
        "orders.html",
        rows=repositories.list_sales_orders(
            database_path,
            str(request.args.get("status", "")).strip(),
            str(request.args.get("keyword", "")).strip(),
            100,
        ),
        items=repositories.list_items(database_path, "finished"),
        warehouses=repositories.list_warehouses(database_path),
        customers=repositories.list_partners(database_path, "customer"),
        current_status=str(request.args.get("status", "")).strip(),
        keyword=str(request.args.get("keyword", "")).strip(),
        platforms=repositories.PLATFORMS,
    )


@main_bp.route("/warehouse-workbench", methods=["GET", "POST"])
@login_required
@roles_required("admin", "warehouse")
def warehouse_workbench():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        action = str(request.form.get("action", "")).strip()
        order_id = int(request.form.get("order_id"))
        try:
            if action == "lock":
                repositories.lock_sales_order(database_path, order_id)
                flash("订单已锁库", "success")
            elif action == "ship":
                repositories.ship_sales_order(
                    database_path,
                    order_id,
                    str(request.form.get("logistics_company", "")).strip(),
                    str(request.form.get("tracking_no", "")).strip(),
                    session.get("username", ""),
                )
                flash("订单已发货并扣减库存", "success")
            elif action == "cancel":
                repositories.cancel_sales_order(database_path, order_id)
                flash("订单已取消并释放锁定库存", "success")
        except Exception as exc:
            flash(f"处理失败：{exc}", "danger")
        return redirect(url_for("main.warehouse_workbench"))
    return render_template(
        "warehouse.html",
        orders=repositories.list_sales_orders(database_path, "", 100),
        stock_rows=repositories.list_stock(database_path),
    )


@main_bp.route("/partners", methods=["GET", "POST"])
@login_required
@roles_required("admin", "purchase", "sales", "finance")
def partners():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        try:
            repositories.save_partner(database_path, request.form)
            flash("客户/供应商已保存", "success")
        except Exception as exc:
            flash(f"保存失败：{exc}", "danger")
        return redirect(url_for("main.partners"))
    return render_template("partners.html", rows=repositories.list_partners(database_path))


@main_bp.route("/accounts", methods=["GET", "POST"])
@login_required
@roles_required("admin", "finance")
def accounts():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        action = str(request.form.get("action", "payment")).strip()
        try:
            if action == "settlement":
                repositories.save_platform_settlement(database_path, request.form)
                flash("平台对账已保存", "success")
            else:
                repositories.receive_payment(database_path, request.form, session.get("username", ""))
                flash("收付款已保存", "success")
        except Exception as exc:
            flash(f"保存失败：{exc}", "danger")
        return redirect(url_for("main.accounts"))
    return render_template(
        "accounts.html",
        rows=repositories.account_summary(database_path),
        partners=repositories.list_partners(database_path),
        entries=repositories.list_account_entries(database_path),
        settlements=repositories.list_platform_settlements(database_path),
    )


@main_bp.route("/returns", methods=["GET", "POST"])
@login_required
@roles_required("admin", "warehouse")
def returns():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        action = str(request.form.get("action", "match")).strip()
        try:
            if action == "sync_return_system":
                result = repositories.sync_return_system_records(database_path, current_app.config["RETURN_SYSTEM_DATABASE_PATH"])
                flash(f"已同步退货系统：新增 {result['created']} 条，更新 {result['updated']} 条", "success")
            else:
                repositories.match_return_inbound(database_path, int(request.form.get("return_id")), int(request.form.get("item_id")))
                flash("退货已匹配并入库", "success")
        except Exception as exc:
            flash(f"处理失败：{exc}", "danger")
        return redirect(url_for("main.returns"))
    return render_template(
        "returns.html",
        rows=repositories.list_return_inbounds(database_path),
        finished_items=repositories.list_items(database_path, "finished"),
        after_sales=repositories.list_after_sales(database_path),
    )


@main_bp.route("/production", methods=["GET", "POST"])
@login_required
@roles_required("admin", "warehouse")
def production():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        action = str(request.form.get("action", "")).strip()
        try:
            if action == "bom":
                repositories.create_bom_line(database_path, request.form)
                flash("组成关系已保存", "success")
            else:
                repositories.create_production(database_path, request.form, session.get("username", ""))
                flash("生产入库和物料/包材领用已保存", "success")
        except Exception as exc:
            flash(f"保存失败：{exc}", "danger")
        return redirect(url_for("main.production"))
    return render_template(
        "production.html",
        finished_items=repositories.list_items(database_path, "finished") + repositories.list_items(database_path, "semi_finished"),
        component_items=repositories.list_items(database_path, "material") + repositories.list_items(database_path, "packaging") + repositories.list_items(database_path, "semi_finished"),
        warehouses=repositories.list_warehouses(database_path),
        bom_lines=repositories.list_bom_lines(database_path),
        production_orders=repositories.list_production_orders(database_path),
    )


@main_bp.route("/users", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def users():
    database_path = current_app.config["DATABASE_PATH"]
    if request.method == "POST":
        try:
            repositories.save_user(database_path, request.form)
            flash("账号已新增", "success")
        except Exception as exc:
            flash(f"新增账号失败：{exc}", "danger")
        return redirect(url_for("main.users"))
    return render_template("users.html", rows=repositories.list_users(database_path))


@main_bp.route("/export/<kind>")
@login_required
def export(kind: str):
    path = repositories.export_report(current_app.config["DATABASE_PATH"], current_app.config["EXPORT_DIR"], kind)
    return send_file(Path(path), as_attachment=True, download_name=Path(path).name)


@main_bp.route("/warehouses", methods=["POST"])
@login_required
def warehouses():
    try:
        repositories.save_warehouse(
            current_app.config["DATABASE_PATH"],
            str(request.form.get("name", "")).strip(),
            str(request.form.get("note", "")).strip(),
        )
        flash("仓库已新增", "success")
    except Exception as exc:
        flash(f"新增仓库失败：{exc}", "danger")
    return redirect(request.referrer or url_for("main.stock"))


@main_bp.route("/locations", methods=["POST"])
@login_required
def locations():
    try:
        repositories.save_location(current_app.config["DATABASE_PATH"], request.form)
        flash("货位已新增", "success")
    except Exception as exc:
        flash(f"新增货位失败：{exc}", "danger")
    return redirect(request.referrer or url_for("main.stock"))


@main_bp.route("/api/returns/inbound", methods=["POST"])
def api_return_inbound():
    token = request.headers.get("X-API-Token", "")
    if token != current_app.config["RETURN_API_TOKEN"]:
        return jsonify({"ok": False, "message": "unauthorized"}), 401
    try:
        result = repositories.handle_return_inbound(current_app.config["DATABASE_PATH"], request.get_json(force=True) or {})
        return jsonify({"ok": True, "result": result})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400


def _lines_from_form(form, price_field: str) -> list[dict]:
    item_ids = form.getlist("item_id")
    warehouse_ids = form.getlist("warehouse_id")
    quantities = form.getlist("quantity")
    prices = form.getlist(price_field)
    lines = []
    for idx, item_id in enumerate(item_ids):
        if not item_id:
            continue
        qty = float(quantities[idx] or 0)
        if qty <= 0:
            continue
        lines.append(
            {
                "item_id": int(item_id),
                "warehouse_id": int(warehouse_ids[idx]),
                "quantity": qty,
                "unit_price": float(prices[idx] or 0),
            }
        )
    return lines
