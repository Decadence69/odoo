from odoo import http
from odoo.http import request
import logging
import json

_logger = logging.getLogger(__name__)

class SquareController(http.Controller):
    @http.route('/payment/square/webhook', type='json', auth='public', csrf=False)
    def square_webhook(self):
        """Process Square webhook notifications"""
        data = request.get_json_data()

        # Get webhook signature
        signature = request.httprequest.headers.get('X-Square-Signature')
        
        # Only get enabled/test Square providers
        provider = request.env['payment.provider'].sudo().search([
            ('code', '=', 'square'),
            ('state', '!=', 'disabled')
        ], limit=1)  # Only get one provider to avoid duplicate processing

        if not provider:
            _logger.warning("No active Square provider found")
            return {'success': False}

        # Verify signature and process webhook
        if provider._square_verify_webhook_signature(json.dumps(data), signature):
            # Process only payment.created and payment.updated events
            event_type = data.get('type')
            if event_type in ['payment.created', 'payment.updated']:
                if provider._handle_square_webhook(data):
                    return {'success': True}

        return {'success': False}

    @http.route('/payment/square/return', type='http', auth='public', csrf=False)
    def square_return(self, **data):
        """Handle the return from Square after payment"""
        reference = data.get('reference')
        
        if not reference:
            return self._get_safe_redirect('/payment/status')
            
        tx = request.env['payment.transaction'].sudo().search([
            ('reference', '=', reference),
            ('provider_code', '=', 'square')
        ], limit=1)
        
        if not tx:
            _logger.warning("No transaction found for reference: %s", reference)
            return self._get_safe_redirect('/payment/status')
            
        if tx.state in ['done', 'error']:
            return self._get_safe_redirect('/payment/status')
        
        # Check payment status
        payment_id = tx.provider_reference
        if payment_id:
            try:
                payment_data = tx.provider_id._square_make_request(
                    f'/v2/online-checkout/payment-links/{payment_id}',
                    method='GET'
                )
                
                status = payment_data.get('payment_link', {}).get('payment_link_status')
                
                if status == 'COMPLETED':
                    tx._set_done()
                elif status in ['EXPIRED', 'CANCELED']:
                    tx._set_error("Payment was not completed")
            except Exception as e:
                _logger.exception("Error checking payment status: %s", str(e))
        
        return self._get_safe_redirect('/payment/status')
    
    @http.route('/payment/square/refresh_form', type='json', auth='user')
    def refresh_square_form(self, provider_id):
        """Endpoint to refresh provider data after state change"""
        if not provider_id:
            return {'success': False, 'error': 'No provider ID provided'}
            
        provider = request.env['payment.provider'].browse(provider_id)
        if not provider.exists() or provider.code != 'square':
            return {'success': False, 'error': 'Invalid provider'}
            
        return {
            'success': True,
            'state': provider.state,
            'square_access_token': provider.square_access_token,
            'square_location_id': provider.square_location_id
        }

    def _get_safe_redirect(self, url):
        """Create a response that safely redirects even when in an iframe"""
        return request.render('sttl_payment_square.iframe_safe_redirect', {
            'redirect_url': url if url.startswith('/') else f"{request.env['ir.config_parameter'].sudo().get_param('web.base.url')}{url}"
        })
