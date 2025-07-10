import logging
import uuid
from werkzeug import urls

from odoo import _, models
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Return Square-specific values for the checkout form """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'square':
            return res

        try:
            payment_link_data = self._square_create_payment_link()
            return {
                'square_payment_link': payment_link_data.get('payment_link', {}).get('url'),
                'square_payment_id': payment_link_data.get('payment_link', {}).get('id'),
            }
        except Exception as e:
            _logger.exception("Failed to create Square payment link")
            return {'error': _("Could not create Square payment link: %s", str(e))}

    def _square_create_payment_link(self):
        """ Create a Square payment link """
        base_url = self.get_base_url()
        return_url = urls.url_join(base_url, f'/payment/status?reference={self.reference}')
        
        payload = {
            'idempotency_key': str(uuid.uuid4()),
            'description': f"Order {self.reference}",
            'quick_pay': {
                'name': f"Order {self.reference}",
                'price_money': {
                    'amount': payment_utils.to_minor_currency_units(self.amount, self.currency_id),
                    'currency': self.currency_id.name,
                },
                'location_id': self.provider_id.square_location_id,
            },
            'checkout_options': {
                'redirect_url': return_url,
                'ask_for_shipping_address': False,
            }
        }
        
        payment_link_data = self.provider_id._square_make_request(
            '/v2/online-checkout/payment-links', 
            payload=payload
        )
        
        payment_link_id = payment_link_data.get('payment_link', {}).get('id')
        if payment_link_id:
            self.provider_reference = payment_link_id
        
        return payment_link_data
