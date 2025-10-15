from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class GeoRedirectConfig(models.Model):
    _name = 'geo.redirect.config'
    _description = 'Geographic Redirect Configuration'
    _order = 'sequence, country_code'
    
    name = fields.Char(string='Name', required=True, help='Display name for this redirect rule')
    country_code = fields.Char(
        string='Country Code',
        required=True,
        size=2,
        help='ISO 3166-1 alpha-2 country code (e.g., TH, KR, US)'
    )
    redirect_url = fields.Char(
        string='Redirect URL',
        required=True,
        help='Full URL to redirect to (e.g., http://th.mrbur.local:8069)'
    )
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    _sql_constraints = [
        ('country_code_unique', 'UNIQUE(country_code)', 'Country code must be unique!')
    ]
    
    @api.constrains('country_code')
    def _check_country_code(self):
        """Validate country code format"""
        for record in self:
            if record.country_code:
                if len(record.country_code) != 2 or not record.country_code.isalpha():
                    raise ValidationError('Country code must be exactly 2 letters (ISO 3166-1 alpha-2)')
                # Check if already uppercase to avoid recursion
                if record.country_code != record.country_code.upper():
                    raise ValidationError('Country code must be in uppercase (e.g., TH, KR, US)')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to auto-uppercase country codes"""
        for vals in vals_list:
            if 'country_code' in vals and vals['country_code']:
                vals['country_code'] = vals['country_code'].upper()
        return super().create(vals_list)
    
    def write(self, vals):
        """Override write to auto-uppercase country codes"""
        if 'country_code' in vals and vals['country_code']:
            vals['country_code'] = vals['country_code'].upper()
        return super().write(vals)