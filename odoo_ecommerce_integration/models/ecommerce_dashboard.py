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
    def _dashboard_currency_symbol(self, company_ids):
        currencies = (
            self.env["res.company"].browse(company_ids).mapped("currency_id")
        )
        return currencies[0].symbol if len(currencies) == 1 else ""

    @api.model
    def _read_sum(self, model, domain, field_name):
        rows = self.env[model]._read_group(domain, [], [f"{field_name}:sum"])
        return float(rows[0][0] or 0.0) if rows else 0.0

    @api.model
    def _distinct_mapping_ids(self, model, field_name, domain):
        groups = self.env[model]._read_group(domain, [field_name], [])
        ids = set()
        for group in groups:
            value = group[0]
            if hasattr(value, "ids"):
                ids.update(value.ids)
            elif value:
                ids.add(value)
        return sorted(ids)

    @api.model
    def _store_provider(self, store):
        return store.sudo().backend_id.sudo().provider or ""

    @api.model
    def _metric_group(
        self,
        key,
        label,
        metric_label,
        description,
        value_type,
        odoo_value,
        store_values,
        *,
        date_filtered,
    ):
        bars = [
            {
                "scope": "odoo",
                "store_id": False,
                "label": "Total Odoo",
                "value": odoo_value,
                "provider": "",
            }
        ]
        for store, value in store_values:
            bars.append(
                {
                    "scope": "store",
                    "store_id": store.id,
                    "label": store.display_name,
                    "value": value,
                    "provider": self._store_provider(store),
                }
            )
        max_value = max([float(bar["value"] or 0.0) for bar in bars] or [0.0])
        return {
            "key": key,
            "label": label,
            "metric_label": metric_label,
            "description": description,
            "value_type": value_type,
            "date_filtered": date_filtered,
            "bars": bars,
            "max_value": max_value,
            "has_data": any(float(bar["value"] or 0.0) > 0 for bar in bars),
        }

    @api.model
    def _dashboard_metric_groups(
        self, company_ids, stores, start_dt, end_dt, start_date, end_date
    ):
        company_domain = [("company_id", "in", company_ids)]
        product_company_domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", company_ids),
        ]
        customer_company_domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", company_ids),
        ]
        sale_domain = company_domain + [
            ("date_order", ">=", start_dt),
            ("date_order", "<", end_dt),
            ("state", "in", ("sale", "done")),
        ]

        odoo_orders = self.env["sale.order"].search_count(sale_domain)
        order_values = []
        for store in stores:
            order_ids = self._distinct_mapping_ids(
                "ecommerce.order.mapping",
                "odoo_sale_order_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("import_status", "=", "imported"),
                    ("odoo_sale_order_id", "!=", False),
                    ("odoo_sale_order_id.company_id", "in", company_ids),
                    ("odoo_sale_order_id.date_order", ">=", start_dt),
                    ("odoo_sale_order_id.date_order", "<", end_dt),
                    ("odoo_sale_order_id.state", "in", ("sale", "done")),
                ],
            )
            order_values.append((store, len(order_ids)))

        customer_domain = customer_company_domain + [
            ("customer_rank", ">", 0),
            ("create_date", ">=", start_dt),
            ("create_date", "<", end_dt),
        ]
        odoo_customers = self.env["res.partner"].search_count(customer_domain)
        customer_values = []
        for store in stores:
            customer_ids = self._distinct_mapping_ids(
                "ecommerce.customer.mapping",
                "odoo_partner_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("odoo_partner_id.customer_rank", ">", 0),
                    ("odoo_partner_id.create_date", ">=", start_dt),
                    ("odoo_partner_id.create_date", "<", end_dt),
                    "|",
                    ("odoo_partner_id.company_id", "=", False),
                    ("odoo_partner_id.company_id", "in", company_ids),
                ],
            )
            customer_values.append((store, len(customer_ids)))

        odoo_products = self.env["product.template"].search_count(
            [("sale_ok", "=", True)] + product_company_domain
        )
        product_values = []
        for store in stores:
            product_ids = self._distinct_mapping_ids(
                "ecommerce.product.mapping",
                "odoo_template_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("odoo_template_id.sale_ok", "=", True),
                    "|",
                    ("odoo_template_id.company_id", "=", False),
                    ("odoo_template_id.company_id", "in", company_ids),
                ],
            )
            product_values.append((store, len(product_ids)))

        odoo_revenue = self._read_sum("sale.order", sale_domain, "amount_total")
        revenue_values = []
        for store in stores:
            order_ids = self._distinct_mapping_ids(
                "ecommerce.order.mapping",
                "odoo_sale_order_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("import_status", "=", "imported"),
                    ("odoo_sale_order_id", "!=", False),
                    ("odoo_sale_order_id.company_id", "in", company_ids),
                    ("odoo_sale_order_id.date_order", ">=", start_dt),
                    ("odoo_sale_order_id.date_order", "<", end_dt),
                    ("odoo_sale_order_id.state", "in", ("sale", "done")),
                ],
            )
            revenue_values.append(
                (
                    store,
                    self._read_sum(
                        "sale.order",
                        [("id", "in", order_ids), ("company_id", "in", company_ids)],
                        "amount_total",
                    )
                    if order_ids
                    else 0.0,
                )
            )

        quant_domain = [
            ("location_id.usage", "=", "internal"),
            "|",
            ("product_id.company_id", "=", False),
            ("product_id.company_id", "in", company_ids),
        ]
        odoo_inventory = self._read_sum("stock.quant", quant_domain, "quantity")
        inventory_values = []
        for store in stores:
            variant_ids = self._distinct_mapping_ids(
                "ecommerce.variant.mapping",
                "odoo_product_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                ],
            )
            inventory_values.append(
                (
                    store,
                    self._read_sum(
                        "stock.quant",
                        quant_domain + [("product_id", "in", variant_ids)],
                        "quantity",
                    )
                    if variant_ids
                    else 0.0,
                )
            )

        invoice_domain = company_domain + [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", start_date),
            ("invoice_date", "<=", end_date),
        ]
        odoo_invoices = self.env["account.move"].search_count(invoice_domain)
        invoice_values = []
        for store in stores:
            move_ids = self._distinct_mapping_ids(
                "ecommerce.invoice.mapping",
                "odoo_move_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("odoo_move_id", "!=", False),
                    ("odoo_move_id.company_id", "in", company_ids),
                    ("odoo_move_id.move_type", "=", "out_invoice"),
                    ("odoo_move_id.state", "=", "posted"),
                    ("odoo_move_id.invoice_date", ">=", start_date),
                    ("odoo_move_id.invoice_date", "<=", end_date),
                ],
            )
            invoice_values.append((store, len(move_ids)))

        issue_domain = [
            ("store_id", "in", stores.ids),
            ("status", "=", "open"),
        ]
        odoo_issues = self.env["ecommerce.sync.issue"].search_count(issue_domain)
        issue_values = [
            (
                store,
                self.env["ecommerce.sync.issue"].search_count(
                    [("store_id", "=", store.id), ("status", "=", "open")]
                ),
            )
            for store in stores
        ]

        return [
            self._metric_group(
                "orders",
                "Orders",
                "Orders",
                "Confirmed Odoo sale orders; store bars count distinct Odoo orders mapped to each store.",
                "integer",
                odoo_orders,
                order_values,
                date_filtered=True,
            ),
            self._metric_group(
                "customers",
                "Customers",
                "New customers",
                "Customers created in the selected period; store bars use distinct mapped customer records.",
                "integer",
                odoo_customers,
                customer_values,
                date_filtered=True,
            ),
            self._metric_group(
                "products",
                "Products",
                "Sellable products",
                "Sellable product templates; store bars count products mapped to each store.",
                "integer",
                odoo_products,
                product_values,
                date_filtered=False,
            ),
            self._metric_group(
                "revenue",
                "Sales / Revenue",
                "Revenue",
                "Confirmed orders in Odoo currency; store bars avoid counting the same order twice within a store.",
                "currency",
                odoo_revenue,
                revenue_values,
                date_filtered=True,
            ),
            self._metric_group(
                "inventory",
                "Inventory",
                "On-hand quantity",
                "Current internal on-hand quantity; store bars use distinct mapped variants.",
                "quantity",
                odoo_inventory,
                inventory_values,
                date_filtered=False,
            ),
            self._metric_group(
                "finance",
                "Finance",
                "Posted invoices",
                "Posted customer invoices in the selected period; store bars use mapped invoices.",
                "integer",
                odoo_invoices,
                invoice_values,
                date_filtered=True,
            ),
            self._metric_group(
                "issues",
                "Open Issues",
                "Open issues",
                "Current open synchronization issues in the selected Store scope.",
                "integer",
                odoo_issues,
                issue_values,
                date_filtered=False,
            ),
        ]

    @api.model
    def get_dashboard_data(self, filters=None):
        filters = filters or {}
        company_ids = self._company_ids(filters)
        start_dt, end_dt, start_date, end_date = self._dates(filters)
        stores = self._scoped_stores(filters)
        result = {
            "company_ids": company_ids,
            "store_ids": stores.ids,
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "has_scope": bool(company_ids),
            "has_stores": bool(stores),
            "currency_symbol": self._dashboard_currency_symbol(company_ids),
            "metric_groups": [],
        }
        if not company_ids:
            return result
        result["metric_groups"] = self._dashboard_metric_groups(
            company_ids,
            stores,
            start_dt,
            end_dt,
            start_date,
            end_date,
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
    def _dashboard_action(self, xmlid, domain):
        action = self.env["ir.actions.act_window"]._for_xml_id(xmlid)
        action["domain"] = domain
        return action

    @api.model
    def get_metric_drilldown(self, metric, scope="odoo", store_id=None, filters=None):
        filters = filters or {}
        company_ids = self._company_ids(filters)
        start_dt, end_dt, start_date, end_date = self._dates(filters)
        stores = self._scoped_stores(filters)
        store = self.env["ecommerce.store"]
        if scope == "store":
            store = stores.filtered(lambda item: item.id == int(store_id or 0))[:1]
            if not store:
                return False
        company_domain = [("company_id", "in", company_ids)]
        sale_domain = company_domain + [
            ("date_order", ">=", start_dt),
            ("date_order", "<", end_dt),
            ("state", "in", ("sale", "done")),
        ]
        customer_domain = [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", company_ids),
            ("customer_rank", ">", 0),
            ("create_date", ">=", start_dt),
            ("create_date", "<", end_dt),
        ]
        product_domain = [
            ("sale_ok", "=", True),
            "|",
            ("company_id", "=", False),
            ("company_id", "in", company_ids),
        ]
        quant_domain = [
            ("location_id.usage", "=", "internal"),
            "|",
            ("product_id.company_id", "=", False),
            ("product_id.company_id", "in", company_ids),
        ]
        invoice_domain = company_domain + [
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_date", ">=", start_date),
            ("invoice_date", "<=", end_date),
        ]

        if metric in ("orders", "revenue"):
            if scope == "odoo":
                return self._dashboard_action("sale.action_orders", sale_domain)
            order_ids = self._distinct_mapping_ids(
                "ecommerce.order.mapping",
                "odoo_sale_order_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("import_status", "=", "imported"),
                    ("odoo_sale_order_id", "!=", False),
                    ("odoo_sale_order_id.company_id", "in", company_ids),
                    ("odoo_sale_order_id.date_order", ">=", start_dt),
                    ("odoo_sale_order_id.date_order", "<", end_dt),
                    ("odoo_sale_order_id.state", "in", ("sale", "done")),
                ],
            )
            return self._dashboard_action(
                "sale.action_orders",
                [("id", "in", order_ids), ("company_id", "in", company_ids)],
            )

        if metric == "customers":
            if scope == "odoo":
                return self._dashboard_action("base.action_partner_form", customer_domain)
            partner_ids = self._distinct_mapping_ids(
                "ecommerce.customer.mapping",
                "odoo_partner_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("odoo_partner_id.customer_rank", ">", 0),
                    ("odoo_partner_id.create_date", ">=", start_dt),
                    ("odoo_partner_id.create_date", "<", end_dt),
                    "|",
                    ("odoo_partner_id.company_id", "=", False),
                    ("odoo_partner_id.company_id", "in", company_ids),
                ],
            )
            return self._dashboard_action(
                "base.action_partner_form", [("id", "in", partner_ids)]
            )

        if metric == "products":
            if scope == "odoo":
                return self._dashboard_action(
                    "product.product_template_action", product_domain
                )
            template_ids = self._distinct_mapping_ids(
                "ecommerce.product.mapping",
                "odoo_template_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("odoo_template_id.sale_ok", "=", True),
                    "|",
                    ("odoo_template_id.company_id", "=", False),
                    ("odoo_template_id.company_id", "in", company_ids),
                ],
            )
            return self._dashboard_action(
                "product.product_template_action", [("id", "in", template_ids)]
            )

        if metric == "inventory":
            if scope == "odoo":
                return self._dashboard_action("stock.stock_quant_action", quant_domain)
            variant_ids = self._distinct_mapping_ids(
                "ecommerce.variant.mapping",
                "odoo_product_id",
                [("store_id", "=", store.id), ("active", "=", True)],
            )
            return self._dashboard_action(
                "stock.stock_quant_action",
                quant_domain + [("product_id", "in", variant_ids)],
            )

        if metric == "finance":
            if scope == "odoo":
                return self._dashboard_action(
                    "account.action_move_out_invoice_type", invoice_domain
                )
            move_ids = self._distinct_mapping_ids(
                "ecommerce.invoice.mapping",
                "odoo_move_id",
                [
                    ("store_id", "=", store.id),
                    ("active", "=", True),
                    ("odoo_move_id", "!=", False),
                    ("odoo_move_id.company_id", "in", company_ids),
                    ("odoo_move_id.move_type", "=", "out_invoice"),
                    ("odoo_move_id.state", "=", "posted"),
                    ("odoo_move_id.invoice_date", ">=", start_date),
                    ("odoo_move_id.invoice_date", "<=", end_date),
                ],
            )
            return self._dashboard_action(
                "account.action_move_out_invoice_type", [("id", "in", move_ids)]
            )

        if metric == "issues":
            domain = [("store_id", "=", store.id), ("status", "=", "open")] if scope == "store" else [
                ("store_id", "in", stores.ids),
                ("status", "=", "open"),
            ]
            return self._dashboard_action(
                "odoo_ecommerce_integration.action_ecommerce_sync_issue", domain
            )
        return False

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
