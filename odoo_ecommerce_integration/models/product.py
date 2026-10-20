from odoo import models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_open_ecommerce_sync_wizard(self):
        self.ensure_one()
        if not self.env["ecommerce.backend"]._ecommerce_provider_selection():
            raise UserError(
                "No installed eCommerce connector provides product synchronization."
            )
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "odoo_ecommerce_integration.action_ecommerce_product_sync_wizard"
        )
        action["context"] = {
            "default_product_ids": [(6, 0, self.product_variant_id.ids)],
        }
        return action
