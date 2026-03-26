# -*- coding: utf-8 -*-
import base64
import io

from odoo import _
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter


def easytech_create_xlsx_attachment(env, filename, sheet_title, rows):
    """Build an XLSX file in memory and return an ir.attachment for download."""
    if not xlsxwriter:
        raise UserError(
            _("Falta la librería xlsxwriter; use exportación CSV o instale dependencias Odoo.")
        )
    buf = io.BytesIO()
    workbook = xlsxwriter.Workbook(buf, {"in_memory": True})
    sheet_name = (sheet_title or "Sheet1")[:31]
    worksheet = workbook.add_worksheet(sheet_name)
    for row_idx, row in enumerate(rows):
        for col_idx, cell in enumerate(row):
            worksheet.write(row_idx, col_idx, cell)
    workbook.close()
    data = base64.b64encode(buf.getvalue())
    return env["ir.attachment"].create(
        {
            "name": filename,
            "type": "binary",
            "datas": data,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
    )


def easytech_download_action(attachment):
    return {
        "type": "ir.actions.act_url",
        "url": f"/web/content/{attachment.id}?download=true",
        "target": "self",
    }
