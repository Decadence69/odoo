# models/payment_provider.py
from odoo import fields, models

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'
    
    code = fields.Selection(
        selection_add=[('salt_edge', 'Salt Edge')],
        ondelete={'salt_edge': 'cascade'}
    )