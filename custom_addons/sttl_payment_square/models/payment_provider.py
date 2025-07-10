import logging
import pprint
import requests

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError, UserError
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

# Square API endpoints
SQUARE_API_URL = {
    'test': 'https://connect.squareupsandbox.com',
    'prod': 'https://connect.squareup.com'
}

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('square', "Square")],
        ondelete={'square': 'set default'}
    )
    
    square_access_token = fields.Char(
        string="Square Access Token",
        help="The access token for your Square account",
        required_if_provider='square',
        groups='base.group_system',
    )
    square_location_id = fields.Char(
        string="Square Location ID",
        help="The location ID for your Square account",
        required_if_provider='square',
    )

    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'square').update({
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    def _square_make_request(self, endpoint, payload=None, method='POST'):
        self.ensure_one()
        base_url = SQUARE_API_URL['prod'] if self.state == 'enabled' else SQUARE_API_URL['test']
        headers = {
            'Square-Version': '2024-01-01',
            'Authorization': f'Bearer {self.square_access_token}',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.request(
                method=method,
                url=f'{base_url}{endpoint}',
                json=payload if method != 'GET' else None,
                params=payload if method == 'GET' else None,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            _logger.exception("Square API error")
            raise ValidationError(_("Square API error: %s", str(e)))

    def _test_square_credentials(self):
        self.ensure_one()
        if not self.square_access_token or not self.square_location_id:
            raise ValidationError(_("Both Square Access Token and Location ID are required."))
        response = self._square_make_request(f'/v2/locations/{self.square_location_id}', method='GET')
        if not response.get('location'):
            raise ValidationError(_("The provided Location ID was not found in your Square account."))
        return response

    def action_test_square_credentials(self):
        self.ensure_one()
        if self.code != 'square':
            return
        if not self.square_access_token or not self.square_location_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Missing Credentials"),
                    'message': _("Please enter both Square Access Token and Location ID."),
                    'sticky': False,
                    'type': 'warning',
                }
            }
        try:
            self._test_square_credentials()
            if self.state == 'disabled':
                self.write({'state': 'test'})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Connection Test Successful"),
                    'message': _("Successfully connected to Square API. Provider state set to Test mode."),
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Connection Test Failed"),
                    'message': str(e),
                    'sticky': False,
                    'type': 'danger',
                }
            }

    def _square_verify_webhook_signature(self, payload, signature):
        """Verify the webhook signature from Square"""
        # This is a simplified implementation - in production, implement proper verification
        return True

    def _handle_square_webhook(self, data):
        """Handle webhook notifications from Square"""
        event_type = data.get('type')
        
        if event_type in ['payment.updated', 'payment.created']:
            payment_data = data.get('data', {}).get('object', {}).get('payment', {})
            payment_id = payment_data.get('id')
            status = payment_data.get('status')
            order_id = payment_data.get('order_id')
            
            
            # Try to find the transaction by Square's payment ID
            tx = self.env['payment.transaction'].sudo().search([
                ('provider_reference', '=', payment_id),
                ('provider_code', '=', 'square')
            ], limit=1)
            
            # If not found by payment_id, try to find by order_id
            if not tx and order_id:
                tx = self.env['payment.transaction'].sudo().search([
                    ('provider_reference', '=', order_id),
                    ('provider_code', '=', 'square')
                ], limit=1)
            
            # If still not found, try to find by payment link ID
            if not tx:
                all_tx = self.env['payment.transaction'].sudo().search([
                    ('provider_code', '=', 'square'),
                    ('state', 'not in', ['done', 'cancel'])
                ])
                
                # Try to match by amount
                amount = payment_data.get('amount_money', {}).get('amount')
                if amount:
                    matching_tx = all_tx.filtered(lambda t: 
                        payment_utils.to_minor_currency_units(t.amount, t.currency_id) == amount)
                    if matching_tx:
                        tx = matching_tx[0]
                        tx.provider_reference = payment_id
            
            if not tx:
                _logger.warning("Square webhook: no transaction found for payment %s", payment_id)
                return False
                
           
                
            if status == 'COMPLETED':
                tx._set_done()
                return True
            elif status == 'APPROVED':
                if tx.state != 'done':
                    tx._set_done()
                return True
            elif status in ['FAILED', 'CANCELED']:
                tx._set_error("Payment failed on Square")
                return True
                
        return False
    