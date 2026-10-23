from datetime import date, datetime, time, timedelta

from odoo import api, fields, models
from odoo.osv import expression


class EcommerceDashboard(models.TransientModel):
    _name = "ecommerce.dashboard"
    _description = "eCommerce Dashboard"

    @api.model
    def _company_ids(self, filters):
        # The dashboard always follows the active Odoo company context.
        return sorted(self.env.companies.ids)

    @api.model
    def _dates(self, filters):
        today = fields.Date.context_today(self)
        start = fields.Date.to_date(filters.get("date_from")) if filters.get("date_from") else today - timedelta(days=30)
        end = fields.Date.to_date(filters.get("date_to")) if filters.get("date_to") else today
        return (
            datetime.combine(start, time.min),
            datetime.combine(end + timedelta(days=1), time.min),
            start,
            end,
        )

    @api.model
    def get_filters(self):
        companies = self.env.companies
        providers = {}
        for item in self.env["ecommerce.backend"]._ecommerce_provider_registry():
            if item.get("code") and item.get("label"):
                providers[item["code"]] = item["label"]
        backends = self.env["ecommerce.backend"].search(
            [("company_id", "in", companies.ids)], order="name"
        )
        stores = self.env["ecommerce.store"].search(
            [("active", "=", True), ("company_id", "in", companies.ids)], order="name"
        )
        return {
            "active_companies": [
                {"id": company.id, "name": company.display_name} for company in companies
            ],
            "providers": [
                {"code": code, "label": label}
                for code, label in sorted(providers.items(), key=lambda item: item[1])
            ],
            "backends": [
                {
                    "id": backend.id,
                    "name": backend.display_name,
                    "provider": backend.provider,
                    "company_id": backend.company_id.id,
                }
                for backend in backends
            ],
            "stores": [
                {
                    "id": store.id,
                    "name": store.display_name,
                    "backend_id": store.backend_id.id,
                    "provider": store.backend_id.provider,
                    "company_id": store.company_id.id,
                }
                for store in stores
            ],
            "default_date_from": (fields.Date.context_today(self) - timedelta(days=30)).isoformat(),
            "default_date_to": fields.Date.context_today(self).isoformat(),
        }

    @api.model
    def _scoped_stores(self, filters):
        company_ids = self._company_ids(filters)
        if not company_ids:
            return self.env["ecommerce.store"]
        domain = [("active", "=", True), ("company_id", "in", company_ids)]
        provider = filters.get("provider")
        backend_id = filters.get("backend_id")
        store_id = filters.get("store_id")
        if provider:
            domain.append(("backend_id.provider", "=", provider))
        if backend_id:
            domain.append(("backend_id", "=", int(backend_id)))
        if store_id:
            domain.append(("id", "=", int(store_id)))
        return self.env["ecommerce.store"].search(domain)

    @api.model
    def _mapping_domain(self, store_ids, active=True):
        domain = [("store_id", "in", store_ids)]
        if active:
            domain.append(("active", "=", True))
        return domain

    @api.model
    def _queue_domain(self, company_ids, store_ids, provider=None, backend_id=None):
        """Deterministic queue filtering using integration-owned metadata.

        Jobs created before this metadata was introduced remain unclassified and
        are excluded when a provider, backend, or Store filter is requested.
        """
        domain = [
            ("company_id", "in", company_ids),
            ("channel", "=like", "ecommerce%"),
        ]
        if provider:
            domain.append(("ecommerce_provider", "=", provider))
        if backend_id:
            domain.append(("ecommerce_backend_id", "=", int(backend_id)))
        if store_ids:
            domain.append(("ecommerce_store_id", "in", store_ids))
        return domain

    @api.model
    def _mapped_ids(self, table, field, store_ids):
        if not store_ids:
            return []
        self.env.cr.execute(
            f"SELECT DISTINCT {field} FROM {table} "
            "WHERE store_id IN %s AND active IS TRUE AND "
            f"{field} IS NOT NULL",
            (tuple(store_ids),),
        )
        return [row[0] for row in self.env.cr.fetchall()]

    @api.model
    def _mapped_coverage_count(self, kind, store_ids, company_ids):
        if not store_ids:
            return 0
        params = [tuple(store_ids)]
        if kind == "products":
            query = """
                SELECT COUNT(DISTINCT m.odoo_template_id)
                  FROM ecommerce_product_mapping m
                  JOIN product_template t ON t.id = m.odoo_template_id
                 WHERE m.store_id IN %s AND m.active IS TRUE
                   AND t.sale_ok IS TRUE AND t.default_code IS NOT NULL
                   AND (t.company_id IS NULL OR t.company_id IN %s)
            """
            params.append(tuple(company_ids))
        elif kind == "variants":
            query = """
                SELECT COUNT(DISTINCT m.odoo_product_id)
                  FROM ecommerce_variant_mapping m
                  JOIN product_product p ON p.id = m.odoo_product_id
                  JOIN product_template t ON t.id = p.product_tmpl_id
                 WHERE m.store_id IN %s AND m.active IS TRUE
                   AND t.sale_ok IS TRUE AND p.default_code IS NOT NULL
                   AND (t.company_id IS NULL OR t.company_id IN %s)
            """
            params.append(tuple(company_ids))
        elif kind == "customers":
            query = """
                SELECT COUNT(DISTINCT m.odoo_partner_id)
                  FROM ecommerce_customer_mapping m
                  JOIN res_partner p ON p.id = m.odoo_partner_id
                 WHERE m.store_id IN %s AND m.active IS TRUE
                   AND p.customer_rank > 0
                   AND (p.company_id IS NULL OR p.company_id IN %s)
            """
            params.append(tuple(company_ids))
        else:
            query = """
                SELECT COUNT(DISTINCT m.odoo_category_id)
                  FROM ecommerce_category_mapping m
                 WHERE m.store_id IN %s AND m.active IS TRUE
            """
        self.env.cr.execute(query, tuple(params))
        return self.env.cr.fetchone()[0] or 0

    @api.model
    def get_dashboard_data(self, filters=None):
        filters = filters or {}
        company_ids = self._company_ids(filters)
        start_dt, end_dt, start_date, end_date = self._dates(filters)
        stores = self._scoped_stores(filters)
        store_ids = stores.ids
        company_scope = sorted(set(stores.mapped("company_id").ids)) or company_ids
        result = {
            "company_ids": company_ids,
            "store_ids": store_ids,
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "has_scope": bool(company_ids),
            "has_stores": bool(store_ids),
            "kpis": [],
            "coverage": {},
            "charts": {},
            "recent_runs": [],
            "failed_jobs": [],
            "open_issues": [],
            "store_health": [],
        }
        if not company_ids:
            return result

        product_company_domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", company_scope or company_ids),
        ]
        eligible_templates = self.env["product.template"].search_count(
            [("sale_ok", "=", True), ("default_code", "!=", False)]
            + product_company_domain
        )
        eligible_variants = self.env["product.product"].search_count(
            [("sale_ok", "=", True), ("default_code", "!=", False)]
            + product_company_domain
        )
        categories = self.env["product.public.category"].search_count([])
        customers = self.env["res.partner"].search_count(
            [
                ("customer_rank", ">", 0),
                "|",
                ("company_id", "=", False),
                ("company_id", "in", company_scope or company_ids),
            ]
        )
        mapped_template_count = self._mapped_coverage_count(
            "products", store_ids, company_scope or company_ids
        )
        mapped_variant_count = self._mapped_coverage_count(
            "variants", store_ids, company_scope or company_ids
        )
        mapped_category_count = self._mapped_coverage_count(
            "categories", store_ids, company_scope or company_ids
        )
        mapped_customer_count = self._mapped_coverage_count(
            "customers", store_ids, company_scope or company_ids
        )
        coverage = {
            "products": {
                "total": eligible_templates,
                "mapped": mapped_template_count,
                "unmapped": max(eligible_templates - mapped_template_count, 0),
            },
            "variants": {
                "total": eligible_variants,
                "mapped": mapped_variant_count,
                "unmapped": max(eligible_variants - mapped_variant_count, 0),
            },
            "categories": {
                "total": categories,
                "mapped": mapped_category_count,
                "unmapped": max(categories - mapped_category_count, 0),
            },
            "customers": {
                "total": customers,
                "mapped": mapped_customer_count,
                "unmapped": max(customers - mapped_customer_count, 0),
            },
        }
        for item in coverage.values():
            item["percent"] = (
                round(item["mapped"] * 100.0 / item["total"], 1)
                if item["total"]
                else 0.0
            )

        order_domain = [
            ("store_id", "in", store_ids),
            ("imported_at", ">=", start_dt),
            ("imported_at", "<", end_dt),
        ]
        order_count = self.env["ecommerce.order.mapping"].search_count(order_domain)
        invoice_domain = [
            ("store_id", "in", store_ids),
            ("create_date", ">=", start_dt),
            ("create_date", "<", end_dt),
        ]
        invoice_count = self.env["ecommerce.invoice.mapping"].search_count(invoice_domain)
        payment_count = self.env["ecommerce.payment.mapping"].search_count(invoice_domain)
        refund_count = self.env["ecommerce.refund.mapping"].search_count(invoice_domain)
        shipment_count = self.env["ecommerce.shipment.mapping"].search_count(invoice_domain)
        revenue = 0.0
        odoo_order_count = 0
        inventory_on_hand = 0.0
        if store_ids:
            self.env.cr.execute(
                """
                SELECT COALESCE(SUM(so.amount_total), 0)
                  FROM sale_order so
                  JOIN ecommerce_order_mapping m ON m.odoo_sale_order_id = so.id
                 WHERE m.store_id IN %s
                   AND so.date_order >= %s AND so.date_order < %s
                """,
                (tuple(store_ids), start_dt, end_dt),
            )
            revenue = self.env.cr.fetchone()[0] or 0.0
            self.env.cr.execute(
                """
                SELECT COUNT(*)
                  FROM sale_order so
                 WHERE so.company_id IN %s
                   AND so.date_order >= %s AND so.date_order < %s
                   AND so.state IN ('sale', 'done')
                """,
                (tuple(company_scope or company_ids), start_dt, end_dt),
            )
            odoo_order_count = self.env.cr.fetchone()[0] or 0
            self.env.cr.execute(
                """
                SELECT COALESCE(SUM(q.quantity), 0)
                  FROM stock_quant q
                  JOIN product_product p ON p.id = q.product_id
                  JOIN product_template t ON t.id = p.product_tmpl_id
                  JOIN ecommerce_variant_mapping m ON m.odoo_product_id = p.id
                 WHERE m.store_id IN %s AND m.active IS TRUE
                   AND (t.company_id IS NULL OR t.company_id IN %s)
                   AND q.location_id IN (
                       SELECT id FROM stock_location WHERE usage = 'internal'
                   )
                """,
                (tuple(store_ids), tuple(company_scope or company_ids)),
            )
            inventory_on_hand = float(self.env.cr.fetchone()[0] or 0.0)
        queue_domain = self._queue_domain(
            company_scope or company_ids,
            store_ids,
            filters.get("provider"),
            filters.get("backend_id"),
        )
        pending_states = ("pending", "enqueued", "wait_dependencies")
        pending = self.env["queue.job"].sudo().search_count(
            queue_domain + [("state", "in", pending_states)]
        )
        running = self.env["queue.job"].sudo().search_count(
            queue_domain + [("state", "=", "started")]
        )
        failed = self.env["queue.job"].sudo().search_count(
            queue_domain + [("state", "=", "failed")]
        )
        issue_domain = [
            ("store_id", "in", store_ids),
            ("status", "=", "open"),
        ]
        open_issues = self.env["ecommerce.sync.issue"].search_count(issue_domain)

        def kpi(key, label, value, suffix=""):
            return {"key": key, "label": label, "value": value, "suffix": suffix}

        result["kpis"] = [
            kpi("products", "Total Products", eligible_templates),
            kpi("mapped_products", "Mapped Products", mapped_template_count),
            kpi("unmapped_products", "Unmapped Products", coverage["products"]["unmapped"]),
            kpi("coverage", "Product Coverage", coverage["products"]["percent"], "%"),
            kpi("mapped_variants", "Mapped Variants", mapped_variant_count),
            kpi("unmapped_variants", "Unmapped Variants", coverage["variants"]["unmapped"]),
            kpi("mapped_categories", "Mapped Categories", mapped_category_count),
            kpi("unmapped_categories", "Unmapped Categories", coverage["categories"]["unmapped"]),
            kpi("mapped_customers", "Mapped Customers", mapped_customer_count),
            kpi("unmapped_customers", "Unmapped Customers", coverage["customers"]["unmapped"]),
            kpi("orders", "eCommerce Orders", order_count),
            kpi("odoo_orders", "Odoo Orders", odoo_order_count),
            kpi("revenue", "eCommerce Revenue", round(revenue, 2)),
            kpi("inventory_on_hand", "On Hand", round(inventory_on_hand, 2)),
            kpi("invoices", "eCommerce Invoices", invoice_count),
            kpi("payments", "eCommerce Payments", payment_count),
            kpi("refunds", "Credit Notes", refund_count),
            kpi("shipments", "Shipments", shipment_count),
            kpi("pending_jobs", "Pending Queue Jobs", pending),
            kpi("running_jobs", "Running Queue Jobs", running),
            kpi("failed_jobs", "Failed Queue Jobs", failed),
            kpi("open_issues", "Open Issues", open_issues),
        ]
        result["coverage"] = coverage
        result["kpi_groups"] = [
            {
                "key": "orders",
                "label": "Orders",
                "kpis": self._kpis_for(result["kpis"], ("orders", "odoo_orders", "revenue", "shipments")),
            },
            {
                "key": "customers",
                "label": "Customers",
                "kpis": self._kpis_for(result["kpis"], ("mapped_customers", "unmapped_customers")),
            },
            {
                "key": "products",
                "label": "Products",
                "kpis": self._kpis_for(result["kpis"], ("products", "mapped_products", "coverage", "unmapped_products", "mapped_variants", "unmapped_variants")),
            },
            {
                "key": "inventory",
                "label": "Inventory",
                "kpis": self._kpis_for(result["kpis"], ("inventory_on_hand", "mapped_variants", "unmapped_variants")),
            },
            {
                "key": "finance",
                "label": "Finance",
                "kpis": self._kpis_for(result["kpis"], ("invoices", "payments", "refunds")),
            },
            {
                "key": "synchronization",
                "label": "Synchronization",
                "kpis": self._kpis_for(result["kpis"], ("pending_jobs", "running_jobs", "failed_jobs", "open_issues")),
            },
        ]
        result["charts"] = {
            "orders": self._order_series(store_ids, start_dt, end_dt, filters.get("granularity", "day")),
            "providers": self._provider_breakdown(store_ids, start_dt, end_dt),
            "queue": self._queue_status(
                company_scope or company_ids,
                store_ids,
                filters.get("provider"),
                filters.get("backend_id"),
            ),
            "activity": self._activity_series(store_ids, start_dt, end_dt),
            "coverage": coverage,
            "order_comparison": self._order_comparison(
                store_ids,
                company_scope or company_ids,
                start_dt,
                end_dt,
                filters.get("granularity", "day"),
            ),
        }
        runs = self.env["ecommerce.sync.run"].search(
            [("store_id", "in", store_ids)], order="started_at desc, id desc", limit=10
        )
        result["recent_runs"] = [
            {
                "id": run.id,
                "provider": run.provider,
                "store": run.store_id.display_name,
                "operation": run.operation,
                "resource": run.resource,
                "state": run.state,
                "started_at": run.started_at.isoformat() if run.started_at else False,
                "processed": run.processed,
                "succeeded": run.succeeded,
                "failed": run.failed,
                "total": run.total,
            }
            for run in runs
        ]
        failed_jobs = self.env["queue.job"].sudo().search(
            queue_domain + [("state", "=", "failed")],
            order="id desc",
            limit=10,
        )
        result["failed_jobs"] = [
            {
                "id": job.id,
                "name": job.name or job.method_name,
                "method": job.method_name,
                "channel": job.channel,
                "company_id": job.company_id.id,
            }
            for job in failed_jobs
        ]
        issues = self.env["ecommerce.sync.issue"].search(
            issue_domain, order="last_seen_at desc, id desc", limit=10
        )
        result["open_issues"] = [
            {
                "id": issue.id,
                "severity": issue.severity,
                "store": issue.store_id.display_name,
                "entity": issue.external_reference or issue.entity_id or issue.title,
                "reason": issue.reason_code,
                "status": issue.status,
            }
            for issue in issues
        ]
        for store in stores[:25]:
            store_queue = self._queue_domain([store.company_id.id], [store.id])
            last_state = self.env["ecommerce.sync.state"].search(
                [("store_id", "=", store.id), ("last_success_at", "!=", False)],
                order="last_success_at desc",
                limit=1,
            )
            result["store_health"].append(
                {
                    "id": store.id,
                    "store": store.display_name,
                    "backend": store.backend_id.display_name,
                    "provider": store.backend_id.provider,
                    "company": store.company_id.display_name,
                    "backend_state": store.backend_id.state,
                    "last_test_at": store.backend_id.last_test_at.isoformat()
                    if store.backend_id.last_test_at
                    else False,
                    "last_success_at": last_state.last_success_at.isoformat()
                    if last_state and last_state.last_success_at
                    else False,
                    "pending": self.env["queue.job"].sudo().search_count(
                        store_queue + [("state", "in", pending_states)]
                    ),
                    "failed": self.env["queue.job"].sudo().search_count(
                        store_queue + [("state", "=", "failed")]
                    ),
                    "issues": self.env["ecommerce.sync.issue"].search_count(
                        [("store_id", "=", store.id), ("status", "=", "open")]
                    ),
                }
            )
        return result

    @staticmethod
    def _kpis_for(kpis, keys):
        by_key = {item["key"]: item for item in kpis}
        return [by_key[key] for key in keys if key in by_key]

    @api.model
    def _order_comparison(self, store_ids, company_ids, start_dt, end_dt, granularity):
        if not store_ids:
            return []
        granularity = granularity if granularity in ("day", "week", "month") else "day"
        self.env.cr.execute(
            f"""
            SELECT date_trunc(%s, so.date_order) AS bucket, COUNT(*)
              FROM sale_order so
             WHERE so.company_id IN %s
               AND so.date_order >= %s AND so.date_order < %s
               AND so.state IN ('sale', 'done')
             GROUP BY bucket
            """,
            (granularity, tuple(company_ids), start_dt, end_dt),
        )
        odoo = {row[0].date().isoformat(): row[1] for row in self.env.cr.fetchall()}
        ecommerce = {
            row["bucket"]: row["count"]
            for row in self._order_series(store_ids, start_dt, end_dt, granularity)
        }
        return [
            {
                "bucket": bucket,
                "odoo_orders": odoo.get(bucket, 0),
                "ecommerce_orders": ecommerce.get(bucket, 0),
            }
            for bucket in sorted(set(odoo) | set(ecommerce))
        ]

    @api.model
    def _order_series(self, store_ids, start_dt, end_dt, granularity):
        if not store_ids:
            return []
        granularity = granularity if granularity in ("day", "week", "month") else "day"
        self.env.cr.execute(
            f"""
            SELECT date_trunc(%s, so.date_order) AS bucket,
                   COUNT(*) AS orders,
                   COALESCE(SUM(so.amount_total), 0) AS revenue
              FROM sale_order so
              JOIN ecommerce_order_mapping m ON m.odoo_sale_order_id = so.id
             WHERE m.store_id IN %s
               AND so.date_order >= %s AND so.date_order < %s
             GROUP BY bucket
             ORDER BY bucket
            """,
            (granularity, tuple(store_ids), start_dt, end_dt),
        )
        return [
            {"bucket": row[0].date().isoformat(), "count": row[1], "revenue": float(row[2] or 0)}
            for row in self.env.cr.fetchall()
        ]

    @api.model
    def _provider_breakdown(self, store_ids, start_dt, end_dt):
        if not store_ids:
            return []
        self.env.cr.execute(
            """
            SELECT b.provider, COUNT(*)
              FROM ecommerce_order_mapping m
              JOIN ecommerce_store s ON s.id = m.store_id
              JOIN ecommerce_backend b ON b.id = s.backend_id
             WHERE m.store_id IN %s
               AND m.imported_at >= %s AND m.imported_at < %s
             GROUP BY b.provider
             ORDER BY b.provider
            """,
            (tuple(store_ids), start_dt, end_dt),
        )
        return [
            {"label": row[0] or "Unknown", "count": row[1]}
            for row in self.env.cr.fetchall()
        ]

    @api.model
    def _queue_status(self, company_ids, store_ids, provider=None, backend_id=None):
        domain = self._queue_domain(company_ids, store_ids, provider, backend_id)
        groups = self.env["queue.job"].sudo().read_group(
            domain, ["state"], ["state"], lazy=False
        )
        mapping = {
            "wait_dependencies": "pending",
            "pending": "pending",
            "enqueued": "pending",
            "started": "running",
            "done": "done",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        values = {}
        for group in groups:
            label = mapping.get(group["state"], group["state"] or "unknown")
            values[label] = values.get(label, 0) + group["__count"]
        unclassified = self.env["queue.job"].sudo().search_count(
            [
                ("company_id", "in", company_ids),
                ("channel", "=like", "ecommerce%"),
                ("ecommerce_provider", "=", False),
            ]
        )
        rows = [{"label": label, "count": count} for label, count in values.items()]
        if unclassified:
            rows.append({"label": "unclassified", "count": unclassified})
        return rows

    @api.model
    def _activity_series(self, store_ids, start_dt, end_dt):
        if not store_ids:
            return []
        self.env.cr.execute(
            """
            SELECT date_trunc('day', occurred_at) AS bucket,
                   severity,
                   COUNT(*)
              FROM ecommerce_sync_event
             WHERE store_id IN %s
               AND occurred_at >= %s AND occurred_at < %s
             GROUP BY bucket, severity
             ORDER BY bucket
            """,
            (tuple(store_ids), start_dt, end_dt),
        )
        result = []
        for bucket, severity, count in self.env.cr.fetchall():
            result.append(
                {
                    "bucket": bucket.date().isoformat(),
                    "severity": severity,
                    "count": count,
                }
            )
        return result

    @api.model
    def get_drilldown(self, key, filters=None):
        filters = filters or {}
        stores = self._scoped_stores(filters)
        store_ids = stores.ids
        if key in ("products", "coverage"):
            companies = stores.mapped("company_id").ids or self._company_ids(filters)
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "product.product_template_action"
            )
            action["domain"] = [
                ("sale_ok", "=", True),
                ("default_code", "!=", False),
                "|",
                ("company_id", "=", False),
                ("company_id", "in", companies),
            ]
            return action
        if key == "mapped_products":
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "odoo_ecommerce_integration.action_ecommerce_product_mapping"
            )
            action["domain"] = self._mapping_domain(store_ids)
            return action
        if key == "unmapped_products":
            mapped = set(self._mapped_ids("ecommerce_product_mapping", "odoo_template_id", store_ids))
            companies = stores.mapped("company_id").ids or self._company_ids(filters)
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "product.product_template_action"
            )
            action["domain"] = [
                ("id", "not in", list(mapped)),
                ("sale_ok", "=", True),
                ("default_code", "!=", False),
                "|",
                ("company_id", "=", False),
                ("company_id", "in", companies),
            ]
            return action
        if key in ("mapped_variants", "unmapped_variants"):
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "odoo_ecommerce_integration.action_ecommerce_variant_mapping"
            )
            if key == "mapped_variants":
                action["domain"] = self._mapping_domain(store_ids)
                return action
            mapped = set(self._mapped_ids("ecommerce_variant_mapping", "odoo_product_id", store_ids))
            action = self.env["ir.actions.act_window"]._for_xml_id("product.product_normal_action")
            action["domain"] = [
                ("id", "not in", list(mapped)),
                ("sale_ok", "=", True),
                ("default_code", "!=", False),
            ]
            return action
        if key in ("mapped_categories", "unmapped_categories"):
            if key == "mapped_categories":
                action = self.env["ir.actions.act_window"]._for_xml_id(
                    "odoo_ecommerce_integration.action_ecommerce_category_mapping"
                )
                action["domain"] = self._mapping_domain(store_ids)
                return action
            mapped = set(self._mapped_ids("ecommerce_category_mapping", "odoo_category_id", store_ids))
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "website_sale.product_public_category_action"
            )
            action["domain"] = [("id", "not in", list(mapped))]
            return action
        if key in ("mapped_customers", "unmapped_customers"):
            if key == "mapped_customers":
                action = self.env["ir.actions.act_window"]._for_xml_id(
                    "odoo_ecommerce_integration.action_ecommerce_customer_mapping"
                )
                action["domain"] = self._mapping_domain(store_ids)
                return action
            mapped = set(self._mapped_ids("ecommerce_customer_mapping", "odoo_partner_id", store_ids))
            action = self.env["ir.actions.act_window"]._for_xml_id("base.action_partner_form")
            action["domain"] = [("id", "not in", list(mapped)), ("customer_rank", ">", 0)]
            return action
        if key in ("orders", "revenue"):
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "odoo_ecommerce_integration.action_ecommerce_order_mapping"
            )
            action["domain"] = [("store_id", "in", store_ids)]
            return action
        if key == "odoo_orders":
            action = self.env["ir.actions.act_window"]._for_xml_id("sale.action_orders")
            companies = stores.mapped("company_id").ids or self._company_ids(filters)
            action["domain"] = [
                ("company_id", "in", companies),
                ("state", "in", ("sale", "done")),
            ]
            return action
        if key == "inventory_on_hand":
            action = self.env["ir.actions.act_window"]._for_xml_id("product.product_normal_action")
            mapped = set(self._mapped_ids("ecommerce_variant_mapping", "odoo_product_id", store_ids))
            action["domain"] = [("id", "in", list(mapped))]
            return action
        if key in ("invoices", "payments", "refunds", "shipments"):
            xmlid = {
                "invoices": "action_ecommerce_invoice_mapping",
                "payments": "action_ecommerce_payment_mapping",
                "refunds": "action_ecommerce_refund_mapping",
                "shipments": "action_ecommerce_shipment_mapping",
            }[key]
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "odoo_ecommerce_integration.%s" % xmlid
            )
            action["domain"] = [("store_id", "in", store_ids)]
            return action
        if key in ("pending_jobs", "running_jobs", "failed_jobs"):
            if not self.env.user.has_group("queue_job.group_queue_job_manager"):
                return False
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "queue_job.action_queue_job"
            )
            companies = stores.mapped("company_id").ids or self._company_ids(filters)
            domain = self._queue_domain(
                companies,
                store_ids,
                filters.get("provider"),
                filters.get("backend_id"),
            )
            if key == "pending_jobs":
                domain = expression.AND([domain, [("state", "in", ("pending", "enqueued", "wait_dependencies"))]])
            elif key == "running_jobs":
                domain = expression.AND([domain, [("state", "=", "started")]])
            else:
                domain = expression.AND([domain, [("state", "=", "failed")]])
            action["domain"] = domain
            return action
        if key == "open_issues":
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "odoo_ecommerce_integration.action_ecommerce_sync_issue"
            )
            action["domain"] = [("store_id", "in", store_ids), ("status", "=", "open")]
            return action
        return False
