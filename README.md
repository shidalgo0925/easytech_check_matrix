# EasyTech — Addons Odoo 18

Raíz de addons para Odoo **Community 18**. Incluye:

| Módulo | Descripción breve |
|--------|-------------------|
| `easytech_check_matrix` | Cheques matriciales: plantillas, diseñador, impresión y numeración por chequera. |
| `easytech_accounting_reports` | Requerimiento de efectivo, libro mayor y antigüedad proveedores, menús EasyTech y enlaces con cheques. |

## Instalación

1. Añadir esta carpeta al `addons_path` de Odoo (junto a `odoo/addons`).
2. Actualizar lista de aplicaciones e instalar en este orden:
   - `easytech_check_matrix`
   - `easytech_accounting_reports` (depende del anterior)

## Requisitos

- Odoo 18 Community
- Módulos estándar: `account`, `purchase` (para informes contables)

## Licencia

LGPL-3 (por módulo; ver `__manifest__.py`).
