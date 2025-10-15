from odoo import models, api
from odoo.http import request


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Only capitalize if it's from website context
            if self._is_website_context():
                if 'name' in vals and vals['name']:
                    vals['name'] = vals['name'].upper()
                if 'company_name' in vals and vals['company_name']:
                    vals['company_name'] = vals['company_name'].upper()
        return super(ResPartner, self).create(vals_list)

    def write(self, vals):
        # Only capitalize if it's from website context
        if self._is_website_context():
            if 'name' in vals and vals['name']:
                vals['name'] = vals['name'].upper()
            if 'company_name' in vals and vals['company_name']:
                vals['company_name'] = vals['company_name'].upper()
        return super(ResPartner, self).write(vals)

    def _is_website_context(self):
        """Check if the operation is happening from website"""
        # Check if website_id is in context (checkout, address forms)
        if self._context.get('website_id'):
            return True
        
        # Check if request is from website (portal/public user actions)
        if request and hasattr(request, 'env') and hasattr(request, 'website'):
            current_user = request.env.user
            # Only apply to portal or public users
            return current_user.has_group('base.group_portal') or \
                   current_user.has_group('base.group_public')
        
        return False


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        users = super(ResUsers, self).create(vals_list)
        
        # Capitalize partner name for newly registered website users
        for user in users:
            if user.has_group('base.group_portal') or user.has_group('base.group_public'):
                if user.partner_id and user.partner_id.name:
                    user.partner_id.with_context(skip_website_check=True).write({
                        'name': user.partner_id.name.upper()
                    })
        
        return users

    def write(self, vals):
        result = super(ResUsers, self).write(vals)
        
        # If name is being updated and user is portal/public, capitalize it
        if 'name' in vals:
            for user in self:
                if user.has_group('base.group_portal') or user.has_group('base.group_public'):
                    if user.partner_id and user.partner_id.name:
                        user.partner_id.with_context(skip_website_check=True).write({
                            'name': user.partner_id.name.upper()
                        })
        
        return result


class ResPartnerWebsiteExtension(models.Model):
    _inherit = 'res.partner'

    def _is_website_context(self):
        """Enhanced check to prevent recursion"""
        if self._context.get('skip_website_check'):
            return False
            
        # Check if website_id is in context (checkout, address forms)
        if self._context.get('website_id'):
            return True
        
        # Check if request is from website (portal/public user actions)
        if request and hasattr(request, 'env') and hasattr(request, 'website'):
            try:
                current_user = request.env.user
                # Only apply to portal or public users
                return current_user.has_group('base.group_portal') or \
                       current_user.has_group('base.group_public')
            except:
                return False
        
        return False