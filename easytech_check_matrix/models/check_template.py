from odoo import api, fields, models, _


class EasytechCheckTemplate(models.Model):
    _name = "easytech.check.template"
    _description = _("Matrix check template")

    name = fields.Char(required=True, string=_("Name"))
    active = fields.Boolean(default=True, string=_("Active"))
    company_id = fields.Many2one(
        "res.company",
        string=_("Company"),
        default=lambda self: self.env.company,
        required=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string=_("Journal"),
        domain="[('type','in',('bank','cash')),('company_id','=',company_id)]",
        help=_("Optional: preferred template for this journal."),
    )

    page_height_mm = fields.Integer(string=_("Page height (mm)"), default=279, required=True)
    page_width_mm = fields.Integer(string=_("Page width (mm)"), default=140, required=True)

    check_print_mode = fields.Selection(
        [
            ("standard", _("Standard (PDF matches template mm)")),
            ("wkhtml_landscape", _("PDF landscape (wide feed / Epson drivers)")),
            ("rotate_ccw90", _("Rotate content 90° counter-clockwise")),
            ("rotate_cw90", _("Rotate content 90° clockwise")),
        ],
        string=_("Print alignment"),
        default="standard",
        help=_(
            "If data prints sideways on preprinted checks (e.g. Banco General + dot matrix), "
            "try “PDF landscape” first, then one of the rotations. "
            "Recalibrate positions in the visual designer after changing this."
        ),
    )

    report_outer_style = fields.Char(compute="_compute_report_canvas_styles")
    report_inner_style = fields.Char(compute="_compute_report_canvas_styles")

    offset_top_mm = fields.Float(string=_("Offset top (mm)"), default=0.0)
    offset_left_mm = fields.Float(string=_("Offset left (mm)"), default=0.0)

    check_no_top_mm = fields.Float(string=_("Check number top (mm)"), default=8.0)
    check_no_left_mm = fields.Float(string=_("Check number left (mm)"), default=112.0)

    date_top_mm = fields.Float(string=_("Date top (mm)"), default=19.0)
    date_left_mm = fields.Float(string=_("Date left (mm)"), default=93.0)

    date_digit_spacing_mm = fields.Float(string=_("Date digit spacing (mm)"), default=4.0)
    date_group_gap_mm = fields.Float(string=_("Date group gap (mm)"), default=3.0)

    beneficiary_top_mm = fields.Float(string=_("Payee top (mm)"), default=31.0)
    beneficiary_left_mm = fields.Float(string=_("Payee left (mm)"), default=12.0)

    amount_num_top_mm = fields.Float(string=_("Amount (figures) top (mm)"), default=41.0)
    amount_num_left_mm = fields.Float(string=_("Amount (figures) left (mm)"), default=90.0)

    amount_txt_top_mm = fields.Float(string=_("Amount (words) top (mm)"), default=40.0)
    amount_txt_left_mm = fields.Float(string=_("Amount (words) left (mm)"), default=12.0)

    voucher_top_mm = fields.Float(string=_("Voucher top (mm)"), default=151.0)
    voucher_left_mm = fields.Float(string=_("Voucher left (mm)"), default=8.0)

    @api.depends(
        "page_width_mm",
        "page_height_mm",
        "check_print_mode",
    )
    def _compute_report_canvas_styles(self):
        for rec in self:
            pw = int(rec.page_width_mm or 0) or 140
            ph = int(rec.page_height_mm or 0) or 279
            mode = rec.check_print_mode or "standard"
            if mode == "rotate_ccw90":
                ow, oh = ph, pw
                rot = -90
                ml = -pw / 2.0
                mt = -ph / 2.0
                rec.report_outer_style = (
                    f"position:relative;width:{ow}mm;height:{oh}mm;margin:0;padding:0;overflow:hidden;"
                )
                rec.report_inner_style = (
                    f"position:absolute;left:50%;top:50%;width:{pw}mm;height:{ph}mm;"
                    f"margin-left:{ml}mm;margin-top:{mt}mm;"
                    f"transform:rotate({rot}deg);transform-origin:center center;"
                )
            elif mode == "rotate_cw90":
                ow, oh = ph, pw
                rot = 90
                ml = -pw / 2.0
                mt = -ph / 2.0
                rec.report_outer_style = (
                    f"position:relative;width:{ow}mm;height:{oh}mm;margin:0;padding:0;overflow:hidden;"
                )
                rec.report_inner_style = (
                    f"position:absolute;left:50%;top:50%;width:{pw}mm;height:{ph}mm;"
                    f"margin-left:{ml}mm;margin-top:{mt}mm;"
                    f"transform:rotate({rot}deg);transform-origin:center center;"
                )
            else:
                rec.report_outer_style = (
                    f"position:relative;width:{pw}mm;height:{ph}mm;margin:0;padding:0;overflow:hidden;"
                )
                rec.report_inner_style = f"position:relative;width:{pw}mm;height:{ph}mm;"

    def action_open_visual_designer(self):
        self.ensure_one()
        version = int((self.write_date or fields.Datetime.now()).timestamp())
        return {
            "type": "ir.actions.act_url",
            "url": f"/easytech/check-template/designer/{self.id}?v={version}",
            "target": "self",
        }
