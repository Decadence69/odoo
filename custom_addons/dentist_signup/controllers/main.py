from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
import logging

_logger = logging.getLogger(__name__)


class DentistAuthSignupHome(AuthSignupHome):

    def get_auth_signup_qcontext(self):
        """Override to include function field in qcontext"""
        qcontext = super(DentistAuthSignupHome, self).get_auth_signup_qcontext()
        
        # Add function from request params
        function = request.params.get('function')
        if function:
            qcontext['function'] = function
            _logger.info('Added function to qcontext: %s', function)
        
        return qcontext

    def _prepare_signup_values(self, qcontext):
        """Override to include function field in signup values"""
        values = super(DentistAuthSignupHome, self)._prepare_signup_values(qcontext)
        
        # Add function to the values if present
        function = qcontext.get('function')
        if function:
            values['function'] = function
            _logger.info('Adding function to signup values: %s', function)
        
        return values

    def _signup_with_values(self, token, values):
        """Override to ensure function is saved to partner"""
        # Extract function value before calling parent
        function_value = values.get('function')
        
        # Call parent method which handles the actual signup
        result = super(DentistAuthSignupHome, self)._signup_with_values(token, values)
        
        # After signup, update the partner with function
        if function_value:
            try:
                # The login value is in the values dict
                login = values.get('login')
                if login:
                    # Find the newly created user by login
                    user = request.env['res.users'].sudo().search([('login', '=', login)], limit=1)
                    if user and user.partner_id:
                        user.partner_id.write({'function': function_value})
                        _logger.info('Updated partner function for user %s: %s', login, function_value)
            except Exception as e:
                _logger.error('Error updating partner function: %s', str(e))
        
        return result