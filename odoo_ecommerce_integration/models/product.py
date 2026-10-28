import re
import unicodedata

from odoo import api, fields, models
from odoo.exceptions import UserError


def ecommerce_url_key(value):
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:255]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ecommerce_short_description = fields.Text(
        string="eCommerce Short Description",
        translate=True,
    )
    ecommerce_url_key = fields.Char(
        string="URL Key",
        copy=False,
        help="Storefront URL key. It is generated from the product name until it is edited manually.",
    )
    ecommerce_url_key_manual = fields.Boolean(
        string="Manual URL Key",
        copy=False,
        readonly=True,
    )
    ecommerce_meta_title = fields.Char(string="Meta Title", translate=True)
    ecommerce_meta_keywords = fields.Char(string="Meta Keywords", translate=True)
    ecommerce_meta_description = fields.Text(string="Meta Description", translate=True)
    ecommerce_image_alt_text = fields.Char(string="Main Image Alt Text")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = vals.get("name")
            url_key = vals.get("ecommerce_url_key")
            if not url_key and name:
                vals["ecommerce_url_key"] = ecommerce_url_key(name)
            elif url_key:
                vals.setdefault(
                    "ecommerce_url_key_manual",
                    bool(name and url_key != ecommerce_url_key(name)),
                )
        return super().create(vals_list)

    def write(self, vals):
        if "name" not in vals and "ecommerce_url_key" not in vals:
            return super().write(vals)

        result = True
        for record in self:
            record_vals = dict(vals)
            new_name = record_vals.get("name", record.name)
            if "ecommerce_url_key" in record_vals:
                key = record_vals.get("ecommerce_url_key") or ecommerce_url_key(new_name)
                record_vals["ecommerce_url_key"] = key
                if "ecommerce_url_key_manual" not in vals:
                    record_vals["ecommerce_url_key_manual"] = (
                        key != ecommerce_url_key(new_name)
                    )
            elif not record.ecommerce_url_key_manual:
                record_vals["ecommerce_url_key"] = ecommerce_url_key(new_name)
            result = super(ProductTemplate, record).write(record_vals) and result
        return result

    @api.onchange("name")
    def _onchange_ecommerce_url_key(self):
        for record in self:
            if not record.ecommerce_url_key_manual:
                record.ecommerce_url_key = ecommerce_url_key(record.name)

    def action_open_ecommerce_sync_wizard(self):
        self.ensure_one()
        if not self.env.is_superuser() and not self.env.user.has_group(
            "odoo_ecommerce_integration.group_ecommerce_operator"
        ):
            from odoo.exceptions import AccessError

            raise AccessError(
                "eCommerce Operator access is required for synchronization."
            )
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


class ProductImage(models.Model):
    _inherit = "product.image"

    ecommerce_alt_text = fields.Char(string="Alt Text")
    ecommerce_media_id = fields.Char(string="eCommerce Media ID", copy=False)
