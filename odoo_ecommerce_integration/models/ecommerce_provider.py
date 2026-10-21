CAPABILITY_DEFINITIONS = {
    "health.preflight": "Store preflight and connection validation",
    "product.import": "Import products from the provider",
    "product.export": "Export new products to the provider",
    "product.update": "Update mapped products at the provider",
    "category.import": "Import eCommerce categories",
    "category.export": "Export Odoo eCommerce categories",
    "customer.import": "Import customers",
    "order.import": "Import orders",
    "inventory.export": "Export inventory quantities",
    "shipment.export": "Export shipments",
    "finance.import": "Import financial documents and payment evidence",
}

SYNC_OPERATIONS = [
    ("import", "Import"),
    ("export", "Export"),
    ("update", "Update"),
]

SYNC_DATA_TYPES = [
    ("products", "Products"),
    ("categories", "Categories"),
    ("customers", "Customers"),
    ("orders", "Orders"),
    ("inventory", "Inventory"),
    ("shipments", "Shipments"),
    ("finance", "Financial Documents"),
]

SYNC_CAPABILITY_MAP = {
    ("import", "products"): "product.import",
    ("export", "products"): "product.export",
    ("update", "products"): "product.update",
    ("import", "categories"): "category.import",
    ("export", "categories"): "category.export",
    ("import", "customers"): "customer.import",
    ("import", "orders"): "order.import",
    ("export", "inventory"): "inventory.export",
    ("export", "shipments"): "shipment.export",
    ("import", "finance"): "finance.import",
}
