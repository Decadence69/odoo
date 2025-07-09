from odoo import fields, models


class PaymentProviderSaltEdge(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('salt_edge', "Salt Edge")],
        ondelete={'salt_edge': 'set default'}
    )
