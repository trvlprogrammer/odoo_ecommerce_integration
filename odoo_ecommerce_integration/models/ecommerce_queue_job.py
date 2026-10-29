from odoo import api, fields, models


class QueueJob(models.Model):
    _inherit = "queue.job"

    ecommerce_store_id = fields.Many2one(
        "ecommerce.store", readonly=True, index=True, ondelete="set null"
    )
    ecommerce_backend_id = fields.Many2one(
        "ecommerce.backend", readonly=True, index=True, ondelete="set null",
        string="Instance",
    )
    ecommerce_provider = fields.Char(readonly=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        store_id = self.env.context.get("ecommerce_store_id")
        backend_id = self.env.context.get("ecommerce_backend_id")
        provider = self.env.context.get("ecommerce_provider")
        for vals in vals_list:
            if store_id and not vals.get("ecommerce_store_id"):
                vals["ecommerce_store_id"] = store_id
            if backend_id and not vals.get("ecommerce_backend_id"):
                vals["ecommerce_backend_id"] = backend_id
            if provider and not vals.get("ecommerce_provider"):
                vals["ecommerce_provider"] = provider
        return super().create(vals_list)
