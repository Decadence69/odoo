from odoo import models

class PaymentProviderSaltEdge(models.Model):
    _inherit = 'payment.provider'

    def _get_feature_support(self):
        res = super()._get_feature_support()
        res['tokenize'].append('salt_edge')
        return res
