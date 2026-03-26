from odoo import fields, models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    easytech_use_check_matrix = fields.Boolean(
        string=_("Use EasyTech matrix check printing")
    )
    easytech_checkbook_id = fields.Many2one(
        "easytech.checkbook",
        string=_("Default checkbook"),
        domain="[('company_id','=',company_id)]",
    )
    easytech_check_template_id = fields.Many2one(
        "easytech.check.template",
        string=_("Check template"),
        domain="[('company_id','=',company_id)]",
    )
