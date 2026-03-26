from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EasytechCheckbook(models.Model):
    _name = "easytech.checkbook"
    _description = "Chequera EasyTech"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    journal_id = fields.Many2one(
        "account.journal",
        required=True,
        domain="[('type','in',('bank','cash')),('company_id','=',company_id)]",
    )
    number_start = fields.Integer(required=True)
    number_end = fields.Integer(required=True)
    current_number = fields.Integer(default=0)

    _sql_constraints = [
        (
            "easytech_checkbook_range",
            "CHECK(number_end >= number_start)",
            "El número final debe ser mayor o igual al inicial.",
        ),
    ]

    @api.constrains("current_number", "number_start", "number_end")
    def _check_current_number(self):
        for rec in self:
            if rec.current_number and rec.current_number < rec.number_start:
                raise ValidationError(_("El número actual no puede ser menor al inicial."))
            if rec.current_number and rec.current_number > rec.number_end:
                raise ValidationError(_("El número actual no puede superar el número final."))

    def get_next_number(self):
        self.ensure_one()
        self.env.cr.execute(
            "SELECT current_number, number_start, number_end FROM easytech_checkbook WHERE id=%s FOR UPDATE",
            [self.id],
        )
        current, start, end = self.env.cr.fetchone()
        next_number = (current or (start - 1)) + 1
        if next_number > end:
            raise ValidationError(
                _("La chequera %s no tiene números disponibles (último: %s).") % (self.display_name, end)
            )
        self.env.cr.execute(
            "UPDATE easytech_checkbook SET current_number=%s WHERE id=%s",
            [next_number, self.id],
        )
        return str(next_number)
