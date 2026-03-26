# -*- coding: utf-8 -*-
import base64
import csv
import io

from odoo import _, fields, models
from odoo.exceptions import UserError


class EasytechVendorLedgerWizard(models.TransientModel):
    _name = "easytech.vendor.ledger.wizard"
    _description = "Libro mayor de proveedores (EasyTech)"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.today)
    partner_ids = fields.Many2many("res.partner", string="Proveedores (vacío = todos)")
    line_ids = fields.One2many(
        "easytech.vendor.ledger.line",
        "wizard_id",
        string="Movimientos",
    )

    def action_load_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        self.env["easytech.vendor.ledger.line"].create(
            self._prepare_ledger_line_vals_list()
        )
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Libro mayor de proveedores"),
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": dict(self.env.context),
        }

    def _payable_lines_domain_base(self):
        return [
            ("parent_state", "=", "posted"),
            ("account_type", "=", "liability_payable"),
            ("company_id", "=", self.company_id.id),
            ("partner_id", "!=", False),
        ]

    def _partners_to_include(self):
        self.ensure_one()
        base = self._payable_lines_domain_base()
        if self.partner_ids:
            return self.partner_ids
        AML = self.env["account.move.line"]
        in_period = AML.search(
            base
            + [("date", ">=", self.date_from), ("date", "<=", self.date_to)],
        )
        with_opening = AML.search(base + [("date", "<", self.date_from)])
        return (in_period.partner_id | with_opening.partner_id).sorted(
            lambda p: p.name or ""
        )

    def _opening_balance(self, partner):
        self.ensure_one()
        domain = self._payable_lines_domain_base() + [
            ("partner_id", "=", partner.id),
            ("date", "<", self.date_from),
        ]
        lines = self.env["account.move.line"].search(domain)
        return sum(lines.mapped("balance"))

    def _prepare_ledger_line_vals_list(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("La fecha inicial no puede ser posterior a la final."))
        vals_list = []
        sequence = 10
        partners = self._partners_to_include().sorted(lambda p: p.name or "")
        AML = self.env["account.move.line"]
        for partner in partners:
            opening = self._opening_balance(partner)
            cum = opening
            period_domain = self._payable_lines_domain_base() + [
                ("partner_id", "=", partner.id),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ]
            period_lines = AML.search(period_domain, order="date, move_id, id")
            if opening and not period_lines:
                vals_list.append(
                    {
                        "wizard_id": self.id,
                        "sequence": sequence,
                        "partner_id": partner.id,
                        "date": self.date_from,
                        "is_opening": True,
                        "label": _("Saldo inicial"),
                        "debit": 0.0,
                        "credit": 0.0,
                        "balance": opening,
                        "cumulative_balance": opening,
                    }
                )
                sequence += 1
                continue
            if opening and period_lines:
                vals_list.append(
                    {
                        "wizard_id": self.id,
                        "sequence": sequence,
                        "partner_id": partner.id,
                        "date": self.date_from,
                        "is_opening": True,
                        "label": _("Saldo inicial"),
                        "debit": 0.0,
                        "credit": 0.0,
                        "balance": opening,
                        "cumulative_balance": cum,
                    }
                )
                sequence += 1
            for line in period_lines:
                cum += line.balance
                vals_list.append(
                    {
                        "wizard_id": self.id,
                        "sequence": sequence,
                        "partner_id": partner.id,
                        "date": line.date,
                        "is_opening": False,
                        "move_id": line.move_id.id,
                        "move_line_id": line.id,
                        "journal_id": line.journal_id.id,
                        "ref": line.move_id.name,
                        "label": line.name or line.move_id.ref or "",
                        "debit": line.debit,
                        "credit": line.credit,
                        "balance": line.balance,
                        "cumulative_balance": cum,
                    }
                )
                sequence += 1
        return vals_list

    def action_export_csv(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Cargue las líneas antes de exportar."))
        buf = io.StringIO()
        writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            [
                "Proveedor",
                "Fecha",
                "Tipo",
                "Asiento",
                "Diario",
                "Etiqueta",
                "Debe",
                "Haber",
                "Saldo línea",
                "Saldo acumulado",
            ]
        )
        for line in self.line_ids.sorted(lambda l: (l.sequence, l.id)):
            writer.writerow(
                [
                    line.partner_id.display_name or "",
                    line.date or "",
                    _("Inicial") if line.is_opening else _("Movimiento"),
                    line.ref or "",
                    line.journal_id.code if line.journal_id else "",
                    line.label or "",
                    line.debit,
                    line.credit,
                    line.balance,
                    line.cumulative_balance,
                ]
            )
        data = base64.b64encode(buf.getvalue().encode("utf-8"))
        att = self.env["ir.attachment"].create(
            {
                "name": "easytech_libro_mayor_proveedores.csv",
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
            raise UserError(_("Cargue las líneas antes de exportar."))
        from .easytech_xlsx_export import (
            easytech_create_xlsx_attachment,
            easytech_download_action,
        )

        rows = [
            [
                "Proveedor",
                "Fecha",
                "Tipo",
                "Asiento",
                "Diario",
                "Etiqueta",
                "Debe",
                "Haber",
                "Saldo línea",
                "Saldo acumulado",
            ]
        ]
        for line in self.line_ids.sorted(lambda l: (l.sequence, l.id)):
            rows.append(
                [
                    line.partner_id.display_name or "",
                    line.date or "",
                    _("Inicial") if line.is_opening else _("Movimiento"),
                    line.ref or "",
                    line.journal_id.code if line.journal_id else "",
                    line.label or "",
                    line.debit,
                    line.credit,
                    line.balance,
                    line.cumulative_balance,
                ]
            )
        att = easytech_create_xlsx_attachment(
            self.env,
            "easytech_libro_mayor_proveedores.xlsx",
            _("Libro mayor"),
            rows,
        )
        return easytech_download_action(att)


class EasytechVendorLedgerLine(models.TransientModel):
    _name = "easytech.vendor.ledger.line"
    _description = "Línea libro mayor proveedores"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "easytech.vendor.ledger.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one("res.partner", string="Proveedor", required=True)
    date = fields.Date()
    is_opening = fields.Boolean()
    move_id = fields.Many2one("account.move", string="Asiento")
    move_line_id = fields.Many2one("account.move.line", string="Apunte")
    journal_id = fields.Many2one("account.journal", string="Diario")
    ref = fields.Char(string="Referencia")
    label = fields.Char(string="Etiqueta")
    debit = fields.Monetary(currency_field="company_currency_id")
    credit = fields.Monetary(currency_field="company_currency_id")
    balance = fields.Monetary(string="Saldo línea", currency_field="company_currency_id")
    cumulative_balance = fields.Monetary(
        string="Saldo acumulado",
        currency_field="company_currency_id",
    )
    company_currency_id = fields.Many2one(
        related="wizard_id.company_id.currency_id",
        readonly=True,
    )
