from odoo import models, fields
class PaymentAcquirerSaltEdge(models.Model):
    _inherit = 'payment_acquirer'

    salt_edge_api_key = fields.Char(string="Salt Edge API Key")
