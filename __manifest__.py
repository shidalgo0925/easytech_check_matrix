{
    "name": "Cheque Matricial EasyTech",
    "summary": "Emisión y previsualización de cheques matriciales multibanco",
    "description": """
Motor de emisión de cheques EasyTech para Odoo Community.

- Basado en account.payment.
- Botón de cheque matricial en pagos.
- Acción masiva desde lista de pagos.
- Previsualización individual o por lote.
- Impresión con control de estado y numeración por chequera.
- Plantillas dinámicas por banco con offsets.
""",
    "version": "18.0.1.0.0",
    "author": "Easy Technology Services Panamá",
    "website": "https://easytech.services",
    "license": "LGPL-3",
    "category": "Accounting",
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
    "installable": True,
    "application": False,
}
