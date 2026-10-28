from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    ecommerce_refund = fields.Boolean(
        default=False,
        copy=False,
        readonly=True,
        index=True,
        help="Set after the provider confirms the credit note was exported as a refund.",
    )

    def action_send_to_ecommerce(self):
        self.ensure_one()
        if self.move_type != "out_refund":
            raise UserError("Only customer credit notes can be sent to eCommerce.")
        if self.state != "posted":
            raise UserError("Post the credit note before sending it to eCommerce.")
        if self.ecommerce_refund:
            raise UserError("This credit note has already been refunded in eCommerce.")
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "odoo_ecommerce_integration.action_ecommerce_refund_export_wizard"
        )
        action["context"] = {"default_move_id": self.id}
        return action


class EcommerceStore(models.Model):
    _inherit = "ecommerce.store"

    def _ecommerce_supports_refund_export(self):
        return False

    def _ecommerce_validate_refund_export(self, move, options):
        return True

    def _ecommerce_enqueue_refund_export(self, move, options):
        raise UserError("The selected Store does not support credit note export.")


class EcommerceRefundExportWizard(models.TransientModel):
    _name = "ecommerce.refund.export.wizard"
    _description = "Export Credit Note to eCommerce"

    move_id = fields.Many2one(
        "account.move",
        required=True,
        readonly=True,
        domain="[('move_type', '=', 'out_refund'), ('state', '=', 'posted')]",
    )
    company_id = fields.Many2one(related="move_id.company_id", readonly=True)
    currency_id = fields.Many2one(related="move_id.currency_id", readonly=True)
    refundable_amount = fields.Monetary(
        related="move_id.amount_total",
        currency_field="currency_id",
        readonly=True,
    )
    store_id = fields.Many2one(
        "ecommerce.store",
        required=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        move_id = values.get("move_id") or self.env.context.get("default_move_id")
        if not move_id and self.env.context.get("active_model") == "account.move":
            move_id = (self.env.context.get("active_ids") or [False])[0]
        if move_id:
            move = self.env["account.move"].browse(int(move_id)).exists()
            values["move_id"] = move.id
            stores = self.env["ecommerce.store"].search(
                [("active", "=", True), ("company_id", "=", move.company_id.id)]
            ).filtered(lambda store: store._ecommerce_supports_refund_export())
            if len(stores) == 1:
                values.setdefault("store_id", stores.id)
        return values

    @api.onchange("move_id")
    def _onchange_move_id(self):
        if self.move_id:
            stores = self.env["ecommerce.store"].search(
                [
                    ("active", "=", True),
                    ("company_id", "=", self.move_id.company_id.id),
                ]
            ).filtered(lambda store: store._ecommerce_supports_refund_export())
            self.store_id = stores[:1] if len(stores) == 1 else False

    def _ecommerce_refund_options(self):
        return {}

    def action_process(self):
        self.ensure_one()
        move = self.move_id
        store = self.store_id
        if not move or move.move_type != "out_refund":
            raise UserError("Select a customer credit note.")
        if move.state != "posted":
            raise UserError("Post the credit note before sending it to eCommerce.")
        if move.ecommerce_refund:
            raise UserError("This credit note has already been refunded in eCommerce.")
        if not store or not store.active:
            raise UserError("Select an active eCommerce Store.")
        if store.company_id != move.company_id:
            raise UserError("The Store and the credit note must belong to the same company.")
        if abs(move.amount_total) <= 0:
            raise UserError("The credit note has no refundable amount.")
        store._ecommerce_require_operator()
        if not store._ecommerce_supports_refund_export():
            raise UserError("The selected Store does not support credit note export.")
        options = self._ecommerce_refund_options()
        store._ecommerce_validate_refund_export(move, options)
        if move.ecommerce_refund:
            return {"type": "ir.actions.act_window_close"}
        store._ecommerce_enqueue_refund_export(move, options)
        return {"type": "ir.actions.act_window_close"}
