def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_name = 'ecommerce_legacy_shipping_product'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'ecommerce_carrier_mapping'
           AND column_name = 'shipping_product_id'
        """
    )
    if not cr.fetchone():
        cr.execute("DROP TABLE ecommerce_legacy_shipping_product")
    cr.execute("ALTER TABLE ecommerce_store DROP COLUMN IF EXISTS shipping_product_id")
        return
    cr.execute(
        """
        UPDATE ecommerce_carrier_mapping AS mapping
           SET shipping_product_id = legacy.shipping_product_id
          FROM ecommerce_legacy_shipping_product AS legacy
         WHERE mapping.store_id = legacy.store_id
           AND mapping.shipping_product_id IS NULL
        """
    )
    cr.execute("DROP TABLE ecommerce_legacy_shipping_product")
    cr.execute("ALTER TABLE ecommerce_store DROP COLUMN IF EXISTS shipping_product_id")
