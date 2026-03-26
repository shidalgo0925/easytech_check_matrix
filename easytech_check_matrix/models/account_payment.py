from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    easytech_check_number = fields.Char(
        string=_("Check number"), copy=False, readonly=True, index=True
    )
    easytech_check_state = fields.Selection(
        [
            ("draft", _("Draft")),
            ("printed", _("Printed")),
            ("cancelled", _("Cancelled")),
        ],
        string=_("Check status"),
        default="draft",
        copy=False,
        readonly=True,
    )
    easytech_printed = fields.Boolean(
        string=_("Check printed"), default=False, copy=False, readonly=True
    )
    easytech_checkbook_id = fields.Many2one(
        "easytech.checkbook", string=_("Checkbook"), copy=False, readonly=True
    )
    easytech_check_template_id = fields.Many2one(
        "easytech.check.template", string=_("Check template"), copy=False
    )

    easytech_is_check = fields.Boolean(compute="_compute_easytech_is_check")

    def _compute_easytech_is_check(self):
        for rec in self:
            method_name = (rec.payment_method_line_id.name or "").lower()
            rec.easytech_is_check = bool(
                rec.payment_type == "outbound"
                and (
                    "check" in method_name
                    or "cheque" in method_name
                    or rec.journal_id.easytech_use_check_matrix
                )
            )

    def _easytech_validate_check_payment(self):
        self.ensure_one()
        if not self.easytech_is_check:
            raise UserError(_("This payment is not flagged as a check."))
        if self.state not in ("posted", "in_process"):
            raise UserError(_("Checks can only be printed on posted or in-process payments."))

    def _easytech_assign_number_if_needed(self):
        self.ensure_one()
        if self.easytech_check_number:
            return
        checkbook = self.easytech_checkbook_id or self.journal_id.easytech_checkbook_id
        if not checkbook:
            raise UserError(_("Configure a checkbook on the journal or on the payment."))
        self.write(
            {
                "easytech_checkbook_id": checkbook.id,
                "easytech_check_number": checkbook.get_next_number(),
            }
        )

    def _easytech_get_template_or_error(self):
        self.ensure_one()
        template = self.journal_id.easytech_check_template_id or self.easytech_check_template_id
        if not template:
            raise UserError(_("Configure a check template on the journal or on the payment."))
        if self.easytech_check_template_id != template:
            self.easytech_check_template_id = template
        return template

    def action_preview_check_matrix(self):
        self.ensure_one()
        if not self.easytech_is_check:
            raise UserError(_("This payment is not flagged as a check."))
        self._easytech_get_template_or_error()
        return self.env.ref("easytech_check_matrix.action_report_easytech_check").report_action(self)

    def action_batch_check_preview(self):
        if not self:
            raise UserError(_("Select at least one payment."))
        invalid = self.filtered(lambda p: not p.easytech_is_check)
        if invalid:
            raise UserError(_("All selected payments must be check payments."))
        for pay in self:
            pay._easytech_get_template_or_error()
        return self.env.ref("easytech_check_matrix.action_report_easytech_check").report_action(self)

    def action_print_check_matrix(self):
        for pay in self:
            pay._easytech_validate_check_payment()
            if pay.easytech_printed:
                raise UserError(_("Check %s has already been printed.") % (pay.easytech_check_number or ""))
            pay._easytech_assign_number_if_needed()
            pay._easytech_get_template_or_error()
            pay.write(
                {
                    "easytech_printed": True,
                    "easytech_check_state": "printed",
                }
            )
        return self.env.ref("easytech_check_matrix.action_report_easytech_check").report_action(self)

    def action_cancel_check_matrix(self):
        for pay in self:
            if pay.easytech_check_state == "cancelled":
                continue
            pay.write({"easytech_check_state": "cancelled"})
