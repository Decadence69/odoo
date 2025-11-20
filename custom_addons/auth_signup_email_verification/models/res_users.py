# -*- coding: utf-8 -*-

import logging
from odoo import api, models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def signup(self, values, token=None):
        """
        Override signup to handle function/occupation field
        This is called during email verification completion
        """
        
        # Extract function before calling parent signup
        function_value = values.get('function')

        # Call parent signup method (creates the user)
        # Handle both return formats: (login, password) or (db, login, password)
        result = super(ResUsers, self).signup(values, token)
        
        # Check what was returned
        if len(result) == 2:
            login, password = result
            db = None
        elif len(result) == 3:
            db, login, password = result
        else:
            _logger.error("Unexpected signup return format: %s", result)
            return result
        
        # After user is created, update the partner with function if it wasn't set
        if function_value:
            try:
                user = self.sudo().search([('login', '=', login)], limit=1)
                if user and user.partner_id:
                    # Check if function is already set
                    if not user.partner_id.function:
                        user.partner_id.write({'function': function_value})
                else:
                    _logger.warning("Could not find user or partner for login: %s", login)
            except Exception as e:
                _logger.error("Error updating partner function: %s", str(e))
        else:
            _logger.warning("No function value found in signup values")
        
        # Return in the same format as received
        if db is not None:
            return db, login, password
        else:
            return login, password