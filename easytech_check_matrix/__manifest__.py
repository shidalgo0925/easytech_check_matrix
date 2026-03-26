{
    "name": "EasyTech Matrix Check",
    "summary": "Matrix check printing and preview on preprinted forms (multi-bank)",
    "description": """
EasyTech matrix check engine for Odoo Community.

- Based on account.payment.
- Matrix check button on payments.
- Batch action from payment list.
- Single or batch preview.
- Printing with status and checkbook numbering.
- Per-bank templates with offsets.
""",
    "version": "18.0.1.0.1",
    "author": "Easy Technology Services Panamá",
    "website": "https://easytech.services",
    "license": "LGPL-3",
    "category": "Accounting",
    "icon": "/easytech_check_matrix/static/description/icon.png",
    "depends": ["account"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/checkbook_views.xml",
        "views/check_template_views.xml",
        "views/account_journal_views.xml",
        "views/account_payment_views.xml",
        "data/server_action.xml",
        "views/designer_templates.xml",
        "report/check_report.xml",
        "report/check_template.xml",
        "report/check_preview_template.xml",
        "report/check_calibration_template.xml"
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": False,
}
