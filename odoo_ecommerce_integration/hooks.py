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


def post_init_hook(env):
    ensure_partial_indexes(env.cr)


def ensure_partial_indexes(cr):
    for table, name, columns, where in INDEXES:
        cr.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {name} "
            f"ON {table} ({columns}) WHERE {where}"
        )
