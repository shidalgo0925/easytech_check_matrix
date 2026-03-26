from odoo import http
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
        response = request.render(
            "easytech_check_matrix.check_template_designer_page",
            {
                "t": template,
                "scale": 3.0,
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
