# -*- coding: utf-8 -*-

from odoo import fields, models, api


# Simplified helper functions - no complex models needed
class SignupFieldHelper(models.AbstractModel):
    """Helper methods for signup field management"""
    _name = 'auth.signup.field.helper'
    _description = 'Signup Field Helper'
    
    @api.model
    def get_field_suggestions(self):
        """Get common field suggestions for admins"""
        return [
            'company_registry',  # Company Registry
            'vat',              # Tax ID
            'website',          # Website URL
            'phone',            # Phone Number
            'mobile',           # Mobile Number
            'street',           # Street Address
            'street2',          # Street Address 2
            'city',             # City
            'zip',              # ZIP Code
            'state_id',         # State
            'country_id',       # Country
            'industry_id',      # Industry
            'ref',              # Internal Reference
            'comment',          # Notes
        ] 