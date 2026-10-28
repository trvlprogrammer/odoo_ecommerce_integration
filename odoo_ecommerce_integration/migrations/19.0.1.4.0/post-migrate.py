from odoo import SUPERUSER_ID, api

from odoo.addons.odoo_ecommerce_integration.models.product import ecommerce_url_key


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    templates = env["product.template"].with_context(active_test=False).search(
        [("ecommerce_url_key", "=", False)]
    )
    for template in templates:
        if template.name:
            template.ecommerce_url_key = ecommerce_url_key(template.name)
