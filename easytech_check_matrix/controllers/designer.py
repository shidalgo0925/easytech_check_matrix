from odoo import http, _
from odoo.http import request


EDITABLE_FIELDS = [
    "offset_top_mm",
    "offset_left_mm",
    "check_no_top_mm",
    "check_no_left_mm",
    "date_top_mm",
    "date_left_mm",
    "beneficiary_top_mm",
    "beneficiary_left_mm",
    "amount_num_top_mm",
    "amount_num_left_mm",
    "amount_txt_top_mm",
    "amount_txt_left_mm",
]


class EasytechCheckDesignerController(http.Controller):

    @http.route("/easytech/check-template/designer/<int:template_id>", type="http", auth="user", website=False)
    def check_template_designer(self, template_id, **kwargs):
        template = request.env["easytech.check.template"].browse(template_id)
        if not template.exists():
            return request.not_found()
        if not request.env.user.has_group("easytech_check_matrix.group_easytech_check_manager"):
            return request.not_found()
        labels = {
            "page_title": _("Matrix check designer v2.1 - %s") % template.name,
            "preview": _("Preview"),
            "calibration": _("Calibration"),
            "back_template": _("Back to template"),
            "positions_mm": _("Positions (mm)"),
            "check_no_x": _("Check no. X"),
            "check_no_y": _("Check no. Y"),
            "date_x": _("Date X"),
            "date_y": _("Date Y"),
            "payee_x": _("Payee X"),
            "payee_y": _("Payee Y"),
            "amount_num_x": _("Amount # X"),
            "amount_num_y": _("Amount # Y"),
            "amount_words_x": _("Amount in words X"),
            "amount_words_y": _("Amount in words Y"),
            "offset_x": _("Offset X"),
            "offset_y": _("Offset Y"),
            "save": _("Save"),
            "refresh": _("Refresh"),
            "hint": _("Drag the blue boxes. The black preview simulates printing."),
            "overlay_check": _("Check no."),
            "overlay_date": _("Date"),
            "overlay_payee": _("Payee"),
            "overlay_amount_num": _("Amount #"),
            "overlay_amount_words": _("Amount in words"),
            "msg_saved": _("Saved"),
            "msg_error_prefix": _("Error:"),
            "msg_unknown": _("Unknown error"),
        }
        response = request.render(
            "easytech_check_matrix.check_template_designer_page",
            {
                "t": template,
                "scale": 3.0,
                "labels": labels,
            },
        )
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @http.route("/easytech/check-template/save", type="json", auth="user", methods=["POST"], csrf=False)
    def save_check_template_positions(self, template_id, values):
        if not request.env.user.has_group("easytech_check_matrix.group_easytech_check_manager"):
            return {"ok": False, "error": "no_permission"}

        template = request.env["easytech.check.template"].browse(int(template_id))
        if not template.exists():
            return {"ok": False, "error": "not_found"}

        vals = {}
        for field_name in EDITABLE_FIELDS:
            if field_name in values:
                try:
                    vals[field_name] = float(values[field_name])
                except Exception:
                    continue

        if vals:
            template.write(vals)
        return {"ok": True, "updated": sorted(vals.keys())}
