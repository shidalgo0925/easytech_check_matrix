# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.depends("can_edit_wizard", "can_group_payments")
    def _compute_group_payment(self):
        super()._compute_group_payment()
        if not self.env.context.get("easytech_group_cash_requirements"):
            return
        for wizard in self:
            if wizard.can_group_payments:
                wizard.group_payment = True

    def action_create_payments(self):
        if not self.env.context.get("easytech_cash_requirements_open_check"):
            return super().action_create_payments()
        if self.is_register_payment_on_draft:
            self.payment_difference_handling = "open"
        payments = self._create_payments()
        if self._context.get("dont_redirect_to_payments"):
            return True
        checks = payments.filtered(lambda p: p.easytech_is_check)
        if checks:
            try:
                return checks.action_batch_check_preview()
            except UserError:
                pass
        return self._easytech_payment_register_list_action(payments)

    def _easytech_payment_register_list_action(self, payments):
        action = {
            "name": _("Payments"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "context": {"create": False},
        }
        if len(payments) == 1:
            action.update({"view_mode": "form", "res_id": payments.id})
        else:
            action.update(
                {"view_mode": "list,form", "domain": [("id", "in", payments.ids)]}
            )
        return action
