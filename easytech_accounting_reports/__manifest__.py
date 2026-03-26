{
    "name": "EasyTech Informes y tesorería",
    "summary": "Tesorería proveedores: requerimiento de efectivo, libro mayor, antigüedad AP; seguimiento de cheques matriciales",
    "description": """
Informes y herramientas de tesorería para cuentas por pagar (Odoo 18 Community), con menú dedicado bajo Contabilidad → Proveedores → EasyTech.

Requisito: requiere el módulo «Cheque matricial EasyTech» (easytech_check_matrix), porque integra pagos y vistas ligadas a ese flujo.

Permisos: el grupo «EasyTech: tesorería e informes» habilita el menú; en la práctica se apoya en permisos de facturación/contabilidad.

— Requerimiento de efectivo —
Asistente para listar facturas de proveedor abiertas (publicadas, no pagadas o parcialmente pagadas), con límite operativo de carga. Permite: elegir compañía y diario de banco; filtrar por proveedores; restringir a facturas vencidas; seleccionar líneas a incluir; ver días de mora y saldo acumulado por proveedor y moneda; actualizar la lista; exportar a CSV y Excel; y abrir el asistente estándar de Odoo «Registrar pago» sobre las facturas marcadas, con diario y método de pago configurables. Opcionalmente puede abrir la vista previa del cheque matricial tras crear el pago (si el pago califica como cheque EasyTech).

— Libro mayor de proveedores —
Informe por rango de fechas sobre cuentas por pagar de proveedores: saldo de apertura antes del periodo, movimientos en el periodo (debe, haber, saldo de línea y acumulado), con filtro opcional de proveedores. Incluye exportación CSV y Excel.

— Antigüedad de saldos proveedores —
Clasificación de saldos pendientes de facturas de compra a una fecha de corte, en tramos de antigüedad (corriente, 1–30, 31–60, 61–90, más de 90 días), en moneda del documento y en moneda de la compañía. Modo detalle por factura o resumen por proveedor. Filtro opcional de proveedores. Exportación CSV y Excel.

— Seguimiento de cheques (EasyTech) —
Accesos directos a: registro de pagos emitidos desde diarios con cheque matricial EasyTech activo; y listado de cheques impresos aún no conciliados con extracto bancario (pendientes de «cobro» en sentido de conciliación).

Autor: Easy Technology Services Panamá.
""",
    "version": "18.0.1.6.2",
    "author": "Easy Technology Services Panamá",
    "website": "https://easytech.services",
    "license": "LGPL-3",
    "category": "Accounting",
    "icon": "/easytech_accounting_reports/static/description/icon.png",
    "depends": ["account", "purchase", "easytech_check_matrix"],
    "data": [
        "security/easytech_security.xml",
        "security/ir.model.access.csv",
        "views/menu_easytech.xml",
        "views/cash_requirement_views.xml",
        "views/payment_actions.xml",
        "views/vendor_reports_views.xml",
    ],
    "images": ["static/description/icon.png"],
    "installable": True,
    "application": False,
}
