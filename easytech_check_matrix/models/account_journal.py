from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    easytech_use_check_matrix = fields.Boolean(string="Usar Cheque Matricial EasyTech")
    easytech_checkbook_id = fields.Many2one(
        "easytech.checkbook",
        string="Chequera por defecto",
        domain="[('company_id','=',company_id)]",
    )
    easytech_check_template_id = fields.Many2one(
        "easytech.check.template",
        string="Plantilla de cheque",
        domain="[('company_id','=',company_id)]",
    )
