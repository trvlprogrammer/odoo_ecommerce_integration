def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'ecommerce_store'
           AND column_name = 'shipping_product_id'
        """
    )
    if not cr.fetchone():
        return
    cr.execute("DROP TABLE IF EXISTS ecommerce_legacy_shipping_product")
    cr.execute(
        """
        CREATE TABLE ecommerce_legacy_shipping_product AS
        SELECT id AS store_id, shipping_product_id
          FROM ecommerce_store
         WHERE shipping_product_id IS NOT NULL
        """
    )
