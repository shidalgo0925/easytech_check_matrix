# -*- coding: utf-8 -*-

from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _easytech_check_matrix_landscape_for_report(self, report_sudo, res_ids):
        """Set wkhtmltopdf landscape when template mode requires swapped page axes."""
        if not res_ids:
            return False
        names = (
            "easytech_check_matrix.report_easytech_check",
            "easytech_check_matrix.report_easytech_check_preview_template",
            "easytech_check_matrix.report_easytech_check_calibration",
        )
        if report_sudo.report_name not in names:
            return False

        if report_sudo.model == "easytech.check.template":
            records = self.env["easytech.check.template"].browse(res_ids)
            modes = [r.check_print_mode or "standard" for r in records]
        elif report_sudo.model == "account.payment":
            records = self.env["account.payment"].browse(res_ids)
            modes = []
            for pay in records:
                tmpl = pay.journal_id.easytech_check_template_id or pay.easytech_check_template_id
                modes.append((tmpl.check_print_mode or "standard") if tmpl else "standard")
        else:
            return False

        if not modes:
            return False
        if len(set(modes)) != 1:
            return False
        return modes[0] == "wkhtml_landscape"

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        report_sudo = self._get_report(report_ref)
        res_ids = res_ids or []
        if self._easytech_check_matrix_landscape_for_report(report_sudo, res_ids):
            return super(
                IrActionsReport, self.with_context(landscape=True)
            )._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
