CONSTRAINTS = (
    "ecommerce_store_store_view_uniq",
    "ecommerce_product_mapping_external_uniq",
    "ecommerce_product_mapping_template_uniq",
    "ecommerce_variant_mapping_external_uniq",
    "ecommerce_variant_mapping_product_uniq",
    "ecommerce_attribute_mapping_external_uniq",
    "ecommerce_attribute_mapping_attribute_uniq",
    "ecommerce_attribute_value_mapping_external_uniq",
    "ecommerce_attribute_value_mapping_value_uniq",
    "ecommerce_category_mapping_external_uniq",
    "ecommerce_category_mapping_category_uniq",
    "ecommerce_customer_mapping_external_uniq",
    "ecommerce_inventory_source_mapping_external_uniq",
    "ecommerce_carrier_mapping_external_uniq",
    "ecommerce_payment_method_mapping_external_uniq",
)

INDEXES = (
    ("ecommerce_store", "ecommerce_store_view_active_uniq", "backend_id, external_store_view_id", "external_store_view_id IS NOT NULL"),
    ("ecommerce_product_mapping", "ecommerce_product_mapping_external_active_uniq", "store_id, external_id", "active IS TRUE"),
    ("ecommerce_product_mapping", "ecommerce_product_mapping_template_active_uniq", "store_id, odoo_template_id", "active IS TRUE"),
    ("ecommerce_variant_mapping", "ecommerce_variant_mapping_external_active_uniq", "store_id, external_id", "active IS TRUE"),
    ("ecommerce_variant_mapping", "ecommerce_variant_mapping_product_active_uniq", "store_id, odoo_product_id", "active IS TRUE"),
    ("ecommerce_attribute_mapping", "ecommerce_attribute_mapping_external_active_uniq", "store_id, external_id", "active IS TRUE"),
    ("ecommerce_attribute_mapping", "ecommerce_attribute_mapping_attribute_active_uniq", "store_id, odoo_attribute_id", "active IS TRUE"),
    ("ecommerce_attribute_value_mapping", "ecommerce_attribute_value_mapping_external_active_uniq", "attribute_mapping_id, external_id", "active IS TRUE"),
    ("ecommerce_attribute_value_mapping", "ecommerce_attribute_value_mapping_value_active_uniq", "attribute_mapping_id, odoo_value_id", "active IS TRUE"),
    ("ecommerce_category_mapping", "ecommerce_category_mapping_external_active_uniq", "store_id, external_id", "active IS TRUE"),
    ("ecommerce_category_mapping", "ecommerce_category_mapping_category_active_uniq", "store_id, odoo_category_id", "active IS TRUE"),
    ("ecommerce_customer_mapping", "ecommerce_customer_mapping_external_active_uniq", "store_id, external_id", "active IS TRUE"),
    ("ecommerce_inventory_source_mapping", "ecommerce_inventory_source_mapping_external_active_uniq", "store_id, external_id", "active IS TRUE"),
    ("ecommerce_carrier_mapping", "ecommerce_carrier_mapping_external_active_uniq", "store_id, external_id", "active IS TRUE"),
    ("ecommerce_payment_method_mapping", "ecommerce_payment_method_mapping_external_active_uniq", "store_id, external_id", "active IS TRUE"),
)


def migrate(cr, version):
    if not version:
        return
    for table, _index, _columns, _where in INDEXES:
        for name in (
            f"{table}_store_view_uniq",
            f"{table}_external_uniq",
            f"{table}_template_uniq",
            f"{table}_product_uniq",
            f"{table}_attribute_uniq",
            f"{table}_value_uniq",
            f"{table}_category_uniq",
        ):
            cr.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
    for table, index_name, columns, where in INDEXES:
        cr.execute(
            f"SELECT {columns}, COUNT(*) FROM {table} WHERE {where} "
            f"GROUP BY {columns} HAVING COUNT(*) > 1 LIMIT 1"
        )
        duplicate = cr.fetchone()
        if duplicate:
            raise RuntimeError(
                "Cannot create partial unique index %s: duplicate active data %s"
                % (index_name, duplicate)
            )
    for table, index_name, columns, where in INDEXES:
        cr.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
            f"ON {table} ({columns}) WHERE {where}"
        )
