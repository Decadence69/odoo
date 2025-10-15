# models/sale_order.py
from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    portal_inventory_synced = fields.Boolean(
        string="Portal Inventory Synced",
        default=False,
        help="Set to True after the user syncs this order to their inventory from the portal."
    )
