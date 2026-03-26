from odoo import fields, models


class EasytechCheckTemplate(models.Model):
    _name = "easytech.check.template"
    _description = "Plantilla de cheque matricial"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    journal_id = fields.Many2one(
        "account.journal",
        domain="[('type','in',('bank','cash')),('company_id','=',company_id)]",
        help="Opcional: plantilla preferida para este diario.",
    )

    page_height_mm = fields.Integer(default=279, required=True)
    page_width_mm = fields.Integer(default=140, required=True)
    offset_top_mm = fields.Float(default=0.0)
    offset_left_mm = fields.Float(default=0.0)

    check_no_top_mm = fields.Float(default=8.0)
    check_no_left_mm = fields.Float(default=112.0)

    date_top_mm = fields.Float(default=19.0)
    date_left_mm = fields.Float(default=93.0)

    date_digit_spacing_mm = fields.Float(default=4.0)
    date_group_gap_mm = fields.Float(default=3.0)

    beneficiary_top_mm = fields.Float(default=31.0)
    beneficiary_left_mm = fields.Float(default=12.0)

    amount_num_top_mm = fields.Float(default=41.0)
    amount_num_left_mm = fields.Float(default=90.0)

    amount_txt_top_mm = fields.Float(default=40.0)
    amount_txt_left_mm = fields.Float(default=12.0)

    voucher_top_mm = fields.Float(default=151.0)
    voucher_left_mm = fields.Float(default=8.0)


    def action_open_visual_designer(self):
        self.ensure_one()
        version = int((self.write_date or fields.Datetime.now()).timestamp())
        return {
            "type": "ir.actions.act_url",
            "url": f"/easytech/check-template/designer/{self.id}?v={version}",
            "target": "self",
        }
