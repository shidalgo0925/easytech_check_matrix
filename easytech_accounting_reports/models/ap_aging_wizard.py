# -*- coding: utf-8 -*-
import base64
import csv
import io
from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError


class EasytechApAgingWizard(models.TransientModel):
    _name = "easytech.ap.aging.wizard"
    _description = "Antigüedad de saldos proveedores (EasyTech)"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    as_of_date = fields.Date(
        string="Fecha de corte",
        required=True,
        default=fields.Date.today,
    )
    partner_ids = fields.Many2many("res.partner", string="Proveedores (vacío = todos)")
    line_mode = fields.Selection(
        [
            ("detail", "Por factura"),
            ("partner", "Resumen por proveedor"),
        ],
        string="Vista",
        default="detail",
        required=True,
    )
    line_ids = fields.One2many(
        "easytech.ap.aging.line",
        "wizard_id",
        string="Facturas",
    )

    def action_load_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        if self.line_mode == "partner":
            vals = self._prepare_partner_summary_vals_list()
        else:
            vals = self._prepare_detail_vals_list()
        self.env["easytech.ap.aging.line"].create(vals)
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Antigüedad proveedores"),
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": dict(self.env.context),
        }

    def _open_moves_domain(self):
        domain = [
            ("move_type", "in", ("in_invoice", "in_refund")),
            ("state", "=", "posted"),
            ("payment_state", "in", ("not_paid", "partial")),
            ("company_id", "=", self.company_id.id),
        ]
        if self.partner_ids:
            domain.append(("partner_id", "in", self.partner_ids.ids))
        return domain

    def _bucket_for_days(self, days_past_due, not_due):
        if not_due or days_past_due <= 0:
            return "current"
        if days_past_due <= 30:
            return "b1_30"
        if days_past_due <= 60:
            return "b31_60"
        if days_past_due <= 90:
            return "b61_90"
        return "b90_plus"

    def _bucket_row_amounts(self, bucket, residual_doc, residual_comp):
        """Split document and company residuals into bucket columns (full amount in one bucket)."""
        row = {
            "amount_current": 0.0,
            "amount_1_30": 0.0,
            "amount_31_60": 0.0,
            "amount_61_90": 0.0,
            "amount_90_plus": 0.0,
            "amount_current_company": 0.0,
            "amount_1_30_company": 0.0,
            "amount_31_60_company": 0.0,
            "amount_61_90_company": 0.0,
            "amount_90_plus_company": 0.0,
        }
        if bucket == "current":
            row["amount_current"] = residual_doc
            row["amount_current_company"] = residual_comp
        elif bucket == "b1_30":
            row["amount_1_30"] = residual_doc
            row["amount_1_30_company"] = residual_comp
        elif bucket == "b31_60":
            row["amount_31_60"] = residual_doc
            row["amount_31_60_company"] = residual_comp
        elif bucket == "b61_90":
            row["amount_61_90"] = residual_doc
            row["amount_61_90_company"] = residual_comp
        else:
            row["amount_90_plus"] = residual_doc
            row["amount_90_plus_company"] = residual_comp
        return row

    def _move_bucket_data(self, move):
        """Return dict with bucket, days_overdue, residuals or None if skip."""
        self.ensure_one()
        company_currency = self.company_id.currency_id
        residual_doc = move.amount_residual
        residual_comp = move.amount_residual_signed
        if move.currency_id.is_zero(residual_doc) and company_currency.is_zero(
            residual_comp
        ):
            return None
        due = move.invoice_date_due or move.date
        not_due = bool(due and due > self.as_of_date)
        days_past_due = (self.as_of_date - due).days if due else 0
        bucket = self._bucket_for_days(days_past_due, not_due)
        return {
            "bucket": bucket,
            "days_overdue": max(0, days_past_due) if not not_due else 0,
            "residual_doc": residual_doc,
            "residual_comp": residual_comp,
        }

    def _prepare_detail_vals_list(self):
        self.ensure_one()
        moves = self.env["account.move"].search(
            self._open_moves_domain(),
            order="partner_id, invoice_date_due, id",
        )
        vals_list = []
        sequence = 10
        for move in moves:
            info = self._move_bucket_data(move)
            if not info:
                continue
            bucket = info["bucket"]
            am = self._bucket_row_amounts(
                bucket, info["residual_doc"], info["residual_comp"]
            )
            vals_list.append(
                {
                    "wizard_id": self.id,
                    "sequence": sequence,
                    "is_partner_total": False,
                    "partner_id": move.partner_id.id,
                    "move_id": move.id,
                    "invoice_date": move.invoice_date,
                    "invoice_date_due": move.invoice_date_due,
                    "currency_id": move.currency_id.id,
                    "amount_residual": info["residual_doc"],
                    "amount_residual_company": info["residual_comp"],
                    "days_overdue": info["days_overdue"],
                    "bucket": bucket,
                    **am,
                }
            )
            sequence += 10
        return vals_list

    def _prepare_partner_summary_vals_list(self):
        self.ensure_one()
        moves = self.env["account.move"].search(
            self._open_moves_domain(),
            order="partner_id, id",
        )
        totals_comp = defaultdict(
            lambda: {
                "current": 0.0,
                "b1_30": 0.0,
                "b31_60": 0.0,
                "b61_90": 0.0,
                "b90_plus": 0.0,
            }
        )
        partner_ids = set()
        for move in moves:
            info = self._move_bucket_data(move)
            if not info:
                continue
            pid = move.partner_id.id
            partner_ids.add(pid)
            b = info["bucket"]
            key = (
                "current"
                if b == "current"
                else "b1_30"
                if b == "b1_30"
                else "b31_60"
                if b == "b31_60"
                else "b61_90"
                if b == "b61_90"
                else "b90_plus"
            )
            totals_comp[pid][key] += info["residual_comp"]

        vals_list = []
        sequence = 10
        company_currency = self.company_id.currency_id
        for partner in self.env["res.partner"].browse(sorted(partner_ids)):
            pid = partner.id
            tc = totals_comp[pid]
            total_comp = sum(tc.values())
            vals_list.append(
                {
                    "wizard_id": self.id,
                    "sequence": sequence,
                    "is_partner_total": True,
                    "partner_id": pid,
                    "move_id": False,
                    "invoice_date": False,
                    "invoice_date_due": False,
                    "currency_id": company_currency.id,
                    "amount_residual": 0.0,
                    "amount_residual_company": total_comp,
                    "days_overdue": 0,
                    "bucket": False,
                    "amount_current": 0.0,
                    "amount_1_30": 0.0,
                    "amount_31_60": 0.0,
                    "amount_61_90": 0.0,
                    "amount_90_plus": 0.0,
                    "amount_current_company": tc["current"],
                    "amount_1_30_company": tc["b1_30"],
                    "amount_31_60_company": tc["b31_60"],
                    "amount_61_90_company": tc["b61_90"],
                    "amount_90_plus_company": tc["b90_plus"],
                }
            )
            sequence += 10
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
                "Factura",
                "Resumen",
                "Fecha factura",
                "Vencimiento",
                "Días vencido",
                "Moneda doc.",
                "Saldo (doc.)",
                "Saldo (compañía)",
                "Corriente",
                "1-30",
                "31-60",
                "61-90",
                "+90",
                "Corriente (comp.)",
                "1-30 (comp.)",
                "31-60 (comp.)",
                "61-90 (comp.)",
                "+90 (comp.)",
            ]
        )
        for line in self.line_ids.sorted(lambda l: (l.partner_id.name or "", l.sequence)):
            writer.writerow(
                [
                    line.partner_id.display_name or "",
                    line.move_id.name if line.move_id else "",
                    _("Sí") if line.is_partner_total else "",
                    line.invoice_date or "",
                    line.invoice_date_due or "",
                    line.days_overdue,
                    line.currency_id.name or "",
                    line.amount_residual,
                    line.amount_residual_company,
                    line.amount_current,
                    line.amount_1_30,
                    line.amount_31_60,
                    line.amount_61_90,
                    line.amount_90_plus,
                    line.amount_current_company,
                    line.amount_1_30_company,
                    line.amount_31_60_company,
                    line.amount_61_90_company,
                    line.amount_90_plus_company,
                ]
            )
        data = base64.b64encode(buf.getvalue().encode("utf-8"))
        suffix = "resumen" if self.line_mode == "partner" else "detalle"
        att = self.env["ir.attachment"].create(
            {
                "name": f"easytech_antiguedad_proveedores_{suffix}.csv",
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
                "Factura",
                "Resumen",
                "Fecha factura",
                "Vencimiento",
                "Días vencido",
                "Moneda doc.",
                "Saldo (doc.)",
                "Saldo (compañía)",
                "Corriente",
                "1-30",
                "31-60",
                "61-90",
                "+90",
                "Corriente (comp.)",
                "1-30 (comp.)",
                "31-60 (comp.)",
                "61-90 (comp.)",
                "+90 (comp.)",
            ]
        ]
        for line in self.line_ids.sorted(lambda l: (l.partner_id.name or "", l.sequence)):
            rows.append(
                [
                    line.partner_id.display_name or "",
                    line.move_id.name if line.move_id else "",
                    _("Sí") if line.is_partner_total else "",
                    line.invoice_date or "",
                    line.invoice_date_due or "",
                    line.days_overdue,
                    line.currency_id.name or "",
                    line.amount_residual,
                    line.amount_residual_company,
                    line.amount_current,
                    line.amount_1_30,
                    line.amount_31_60,
                    line.amount_61_90,
                    line.amount_90_plus,
                    line.amount_current_company,
                    line.amount_1_30_company,
                    line.amount_31_60_company,
                    line.amount_61_90_company,
                    line.amount_90_plus_company,
                ]
            )
        suffix = "resumen" if self.line_mode == "partner" else "detalle"
        att = easytech_create_xlsx_attachment(
            self.env,
            f"easytech_antiguedad_proveedores_{suffix}.xlsx",
            _("Antigüedad AP"),
            rows,
        )
        return easytech_download_action(att)


class EasytechApAgingLine(models.TransientModel):
    _name = "easytech.ap.aging.line"
    _description = "Línea antigüedad proveedores"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "easytech.ap.aging.wizard",
        required=True,
        ondelete="cascade",
    )
    is_partner_total = fields.Boolean(string="Resumen proveedor")
    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one("res.partner", string="Proveedor", required=True)
    move_id = fields.Many2one("account.move", string="Factura")
    invoice_date = fields.Date()
    invoice_date_due = fields.Date()
    currency_id = fields.Many2one("res.currency", string="Moneda documento")
    company_currency_id = fields.Many2one(
        related="wizard_id.company_id.currency_id",
        string="Moneda compañía",
        readonly=True,
    )
    amount_residual = fields.Monetary(
        string="Saldo (documento)",
        currency_field="currency_id",
    )
    amount_residual_company = fields.Monetary(
        string="Saldo (compañía)",
        currency_field="company_currency_id",
    )
    days_overdue = fields.Integer(string="Días vencido")
    bucket = fields.Selection(
        [
            ("current", "Corriente / no vencido"),
            ("b1_30", "1 a 30 días"),
            ("b31_60", "31 a 60 días"),
            ("b61_90", "61 a 90 días"),
            ("b90_plus", "Más de 90 días"),
        ],
        string="Tramo",
    )
    amount_current = fields.Monetary(
        string="Corriente",
        currency_field="currency_id",
    )
    amount_1_30 = fields.Monetary(
        string="1-30",
        currency_field="currency_id",
    )
    amount_31_60 = fields.Monetary(
        string="31-60",
        currency_field="currency_id",
    )
    amount_61_90 = fields.Monetary(
        string="61-90",
        currency_field="currency_id",
    )
    amount_90_plus = fields.Monetary(
        string="+90",
        currency_field="currency_id",
    )
    amount_current_company = fields.Monetary(
        string="Corriente (comp.)",
        currency_field="company_currency_id",
    )
    amount_1_30_company = fields.Monetary(
        string="1-30 (comp.)",
        currency_field="company_currency_id",
    )
    amount_31_60_company = fields.Monetary(
        string="31-60 (comp.)",
        currency_field="company_currency_id",
    )
    amount_61_90_company = fields.Monetary(
        string="61-90 (comp.)",
        currency_field="company_currency_id",
    )
    amount_90_plus_company = fields.Monetary(
        string="+90 (comp.)",
        currency_field="company_currency_id",
    )
