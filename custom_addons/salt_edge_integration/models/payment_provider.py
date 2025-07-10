from odoo import fields, models

class PaymentProviderSaltEdge(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('salt_edge', "Salt Edge")],
        ondelete={'salt_edge': 'set default'}
    )

    def _get_supported_payment_method_codes(self):
        if self.code == 'salt_edge':
            return ['salt_edge']
        return super()._get_supported_payment_method_codes()
