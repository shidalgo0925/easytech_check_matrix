# -*- coding: utf-8 -*-
import base64
import csv
import io
from collections import defaultdict
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EasytechCashRequirementWizard(models.TransientModel):
    _name = "easytech.cash.requirement.wizard"
    _description = "Requerimiento de efectivo (EasyTech)"

    @api.model
    def _easytech_default_outbound_payment_method_line(self, journal):
        if not journal:
            return self.env["account.payment.method.line"]
        lines = journal.outbound_payment_method_line_ids
        if not lines:
            return self.env["account.payment.method.line"]
        check = lines.filtered(
            lambda l: "check" in (l.name or "").lower() or "cheque" in (l.name or "").lower()
        )
        if not check and journal.easytech_use_check_matrix:
            check = lines[:1]
        return check[:1] if check else lines[:1]

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario de banco",
        required=True,
        domain="[('type', '=', 'bank'), ('company_id', '=', company_id)]",
        check_company=True,
    )
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line",
        string="Método de pago (cheque)",
        domain="[('id', 'in', available_payment_method_line_ids)]",
        help="Si se deja vacío, se intentará detectar un método de cheque en el diario.",
    )
    available_payment_method_line_ids = fields.Many2many(
        "account.payment.method.line",
        compute="_compute_available_payment_method_line_ids",
    )
    partner_ids = fields.Many2many("res.partner", string="Filtrar proveedores")
    only_overdue = fields.Boolean(string="Solo facturas vencidas")
    open_check_preview_after_payment = fields.Boolean(
        string="Abrir vista previa del cheque al crear el pago",
        default=True,
        help="Si está activo y el pago es por cheque EasyTech, tras confirmar se abre el PDF de previsualización. "
        "Desactívelo si prefiere solo ir a la lista de pagos.",
    )
    line_ids = fields.One2many(
        "easytech.cash.requirement.line",
        "wizard_id",
        string="Facturas proveedor",
    )

    @api.depends("journal_id")
    def _compute_available_payment_method_line_ids(self):
        for wiz in self:
            if wiz.journal_id:
                wiz.available_payment_method_line_ids = wiz.journal_id.outbound_payment_method_line_ids
            else:
                wiz.available_payment_method_line_ids = False

    @api.onchange("journal_id")
    def _onchange_journal_default_payment_method(self):
        for wiz in self:
            wiz.payment_method_line_id = wiz._easytech_default_outbound_payment_method_line(
                wiz.journal_id
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company
        if "company_id" in fields_list and not res.get("company_id"):
            res["company_id"] = company.id
        cid = res.get("company_id") or company.id
        journal = False
        if "journal_id" in fields_list and not res.get("journal_id"):
            journal = self.env["account.journal"].search(
                [("company_id", "=", cid), ("type", "=", "bank")], limit=1
            )
            if journal:
                res["journal_id"] = journal.id
        else:
            jid = res.get("journal_id")
            if jid:
                journal = self.env["account.journal"].browse(jid)
        if (
            journal
            and "payment_method_line_id" in fields_list
            and not res.get("payment_method_line_id")
        ):
            pml = self._easytech_default_outbound_payment_method_line(journal)
            if pml:
                res["payment_method_line_id"] = pml.id
        if "line_ids" in fields_list and "line_ids" not in res:
            moves = self._search_vendor_open_moves(
                company_id=cid,
                partner_ids=False,
                only_overdue=False,
            )
            res["line_ids"] = [
                (0, 0, {"move_id": m.id, "selected": True}) for m in moves
            ]
        return res

    def _search_vendor_open_moves(self, company_id, partner_ids, only_overdue):
        cid = company_id.id if getattr(company_id, "id", None) else company_id
        domain = [
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("company_id", "=", cid),
        ]
        if partner_ids:
            domain.append(("partner_id", "in", partner_ids.ids))
        if only_overdue:
            domain.append(("invoice_date_due", "<", fields.Date.context_today(self)))
        return self.env["account.move"].search(
            domain, order="partner_id, invoice_date_due, id", limit=2000
        )

    def action_reload_lines(self):
        self.ensure_one()
        moves = self._search_vendor_open_moves(
            self.company_id,
            self.partner_ids,
            self.only_overdue,
        )
        self.line_ids = [(5, 0, 0)] + [(0, 0, {"move_id": m.id, "selected": True}) for m in moves]
        return {
            "type": "ir.actions.act_window",
            "name": _("Requerimiento de efectivo"),
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": dict(self.env.context),
        }

    def _gather_payable_lines(self, moves):
        self.ensure_one()
        valid_types = self.env["account.payment"]._get_valid_payment_account_types()
        lines = self.env["account.move.line"]
        for move in moves:
            for line in move.line_ids:
                if line.account_type not in valid_types:
                    continue
                if line.currency_id:
                    if line.currency_id.is_zero(line.amount_residual_currency):
                        continue
                else:
                    if line.company_currency_id.is_zero(line.amount_residual):
                        continue
                lines |= line
        return lines

    def action_register_payment(self):
        self.ensure_one()
        moves = self.line_ids.filtered("selected").mapped("move_id")
        if not moves:
            raise UserError(_("Seleccione al menos una factura con saldo."))
        if len(moves.company_id) > 1:
            raise UserError(_("Todas las facturas deben ser de la misma compañía."))
        lines = self._gather_payable_lines(moves)
        if not lines:
            raise UserError(_("No hay líneas por pagar en las facturas seleccionadas."))
        if len(set(lines.mapped("account_type"))) > 1:
            raise UserError(
                _("No se pueden mezclar cuentas por cobrar y por pagar en un mismo registro.")
            )
        ctx = {
            "active_model": "account.move.line",
            "active_ids": lines.ids,
            "default_journal_id": self.journal_id.id,
            "easytech_group_cash_requirements": True,
        }
        if self.open_check_preview_after_payment:
            ctx["easytech_cash_requirements_open_check"] = True
        if self.payment_method_line_id:
            ctx["default_payment_method_line_id"] = self.payment_method_line_id.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Registrar pago"),
            "res_model": "account.payment.register",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def action_export_csv(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Cargue o actualice la lista antes de exportar."))
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                _("Incluir"),
                _("Proveedor"),
                _("Número"),
                _("Fecha factura"),
                _("Vencimiento"),
                _("Días vencidos"),
                _("Saldo"),
                _("Moneda"),
                _("Saldo acumulado (proveedor/moneda)"),
            ]
        )
        for line in self.line_ids.sorted(
            lambda l: (l.partner_id.name or "", l.invoice_date_due or date.min, l.move_id.id)
        ):
            writer.writerow(
                [
                    _("Sí") if line.selected else _("No"),
                    line.partner_id.display_name or "",
                    line.name or "",
                    line.invoice_date or "",
                    line.invoice_date_due or "",
                    line.days_overdue,
                    line.amount_residual,
                    line.currency_id.name or "",
                    line.partner_running_balance,
                ]
            )
        data = base64.b64encode(buf.getvalue().encode("utf-8"))
        att = self.env["ir.attachment"].create(
            {
                "name": "easytech_requerimiento_efectivo.csv",
                "type": "binary",
                "datas": data,
                "mimetype": "text/csv",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{att.id}?download=true",
            "target": "self",
        }

    def action_export_xlsx(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Cargue o actualice la lista antes de exportar."))
        from .easytech_xlsx_export import (
            easytech_create_xlsx_attachment,
            easytech_download_action,
        )

        rows = [
            [
                _("Incluir"),
                _("Proveedor"),
                _("Número"),
                _("Fecha factura"),
                _("Vencimiento"),
                _("Días vencidos"),
                _("Saldo"),
                _("Moneda"),
                _("Saldo acumulado (proveedor/moneda)"),
            ]
        ]
        for line in self.line_ids.sorted(
            lambda l: (l.partner_id.name or "", l.invoice_date_due or date.min, l.move_id.id)
        ):
            rows.append(
                [
                    _("Sí") if line.selected else _("No"),
                    line.partner_id.display_name or "",
                    line.name or "",
                    line.invoice_date or "",
                    line.invoice_date_due or "",
                    line.days_overdue,
                    line.amount_residual,
                    line.currency_id.name or "",
                    line.partner_running_balance,
                ]
            )
        att = easytech_create_xlsx_attachment(
            self.env,
            "easytech_requerimiento_efectivo.xlsx",
            _("Requerimiento efectivo"),
            rows,
        )
        return easytech_download_action(att)


class EasytechCashRequirementLine(models.TransientModel):
    _name = "easytech.cash.requirement.line"
    _description = "Línea requerimiento efectivo"
    _order = "partner_id, invoice_date_due, move_id"

    wizard_id = fields.Many2one(
        "easytech.cash.requirement.wizard",
        required=True,
        ondelete="cascade",
    )
    selected = fields.Boolean(default=True)
    move_id = fields.Many2one("account.move", required=True, readonly=True)
    partner_id = fields.Many2one(related="move_id.partner_id", store=True, readonly=True)
    invoice_date = fields.Date(related="move_id.invoice_date", readonly=True)
    invoice_date_due = fields.Date(related="move_id.invoice_date_due", readonly=True)
    name = fields.Char(related="move_id.name", string="Número", readonly=True)
    amount_residual = fields.Monetary(
        related="move_id.amount_residual",
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(related="move_id.currency_id", readonly=True)
    days_overdue = fields.Integer(compute="_compute_days_overdue")
    partner_running_balance = fields.Monetary(
        string="Saldo acumulado (proveedor/moneda)",
        currency_field="currency_id",
        compute="_compute_partner_running_balance",
    )

    @api.depends("invoice_date_due")
    def _compute_days_overdue(self):
        today = fields.Date.context_today(self)
        for line in self:
            due = line.invoice_date_due
            if due and due < today:
                line.days_overdue = (today - due).days
            else:
                line.days_overdue = 0

    @api.depends(
        "wizard_id.line_ids",
        "wizard_id.line_ids.move_id",
        "wizard_id.line_ids.amount_residual",
        "amount_residual",
        "partner_id",
        "currency_id",
    )
    def _compute_partner_running_balance(self):
        for wizard in self.mapped("wizard_id"):
            sorted_lines = wizard.line_ids.sorted(
                lambda l: (
                    l.partner_id.id,
                    l.currency_id.id,
                    l.invoice_date_due or date.min,
                    l.move_id.id,
                )
            )
            running = defaultdict(float)
            for line in sorted_lines:
                key = (line.partner_id.id, line.currency_id.id)
                running[key] += line.amount_residual
                line.partner_running_balance = running[key]
