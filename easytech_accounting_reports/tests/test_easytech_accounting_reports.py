# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install", "easytech_accounting")
class TestEasytechAccountingReports(AccountTestInvoicingCommon):
    """Smoke tests for wizards (require account + easytech_check_matrix)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def _create_posted_vendor_bill(self, amount=100.0):
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": fields.Date.today(),
                "invoice_date_due": fields.Date.today(),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "price_unit": amount,
                            "tax_ids": [],
                        },
                    )
                ],
            }
        )
        move.action_post()
        return move

    def test_ap_aging_wizard_loads_vendor_lines(self):
        self._create_posted_vendor_bill()
        wiz = self.env["easytech.ap.aging.wizard"].create(
            {
                "company_id": self.env.company.id,
                "as_of_date": fields.Date.today(),
                "line_mode": "detail",
            }
        )
        wiz.action_load_lines()
        self.assertTrue(wiz.line_ids, "Aging should list open vendor bills.")
        line = wiz.line_ids[0]
        self.assertTrue(line.amount_residual_company)

    def test_vendor_ledger_wizard_loads_payable_lines(self):
        self._create_posted_vendor_bill()
        today = fields.Date.today()
        wiz = self.env["easytech.vendor.ledger.wizard"].create(
            {
                "company_id": self.env.company.id,
                "date_from": today.replace(day=1),
                "date_to": today,
            }
        )
        wiz.action_load_lines()
        self.assertTrue(wiz.line_ids, "Vendor ledger should show payable lines.")

    def test_cash_requirement_wizard_opens_register_action(self):
        self._create_posted_vendor_bill()
        wiz = self.env["easytech.cash.requirement.wizard"].create(
            {
                "company_id": self.env.company.id,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )
        wiz.action_reload_lines()
        self.assertTrue(wiz.line_ids)
        action = wiz.action_register_payment()
        self.assertEqual(action.get("res_model"), "account.payment.register")


@tagged("post_install", "-at_install", "easytech_accounting")
class TestEasytechAccountingReportsStandalone(TransactionCase):
    """Light checks that do not need full invoice setup."""

    def test_module_models_exist(self):
        self.assertIn("easytech.ap.aging.wizard", self.env)
        self.assertIn("easytech.vendor.ledger.wizard", self.env)
        self.assertIn("easytech.cash.requirement.wizard", self.env)
