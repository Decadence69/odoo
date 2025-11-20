# -*- coding: utf-8 -*-

import logging
from odoo import api, models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Email verification flag
    email_verified = fields.Boolean(
        string='Email Verified',
        default=False,
        help="Indicates if the email address has been verified"
    )
    
    # Store user data during signup verification
    signup_user_data = fields.Json(
        string='Signup User Data',
        help="Temporary storage for user data during email verification"
    )
    
    # NEW: Store subdomain for verification URL
    signup_subdomain = fields.Char(
        string='Signup Subdomain',
        help='The subdomain used during signup for verification URL generation'
    )

    def signup_prepare_with_verification(self, user_data):
        """Prepare signup with email verification step"""
        self.ensure_one()
        
        # Clean user data - remove fields that don't exist on res.users model
        # Keep the custom field for our internal logic but don't pass it to Odoo's signup
        # IMPORTANT: Keep 'function' in the clean data so it's preserved!
        clean_user_data = {
            key: value for key, value in user_data.items()
            if key in ['name', 'login', 'password', 'lang', 'is_company', 'company_name', 'function']
        }
        
        # Store clean user data for later use (without signup_company_type)
        self.write({
            'signup_user_data': clean_user_data,
            'signup_type': 'signup',
            'email_verified': False
        })
        
        # Generate signup token using Odoo's official method
        token = self._generate_signup_token()
        
        # Send verification email
        self._send_verification_email()
        
        _logger.info("Email verification initiated for: %s", self.email)
        return self._generate_signup_token()

    def _send_verification_email(self):
        """Send verification email using Odoo's mail template system"""
        self.ensure_one()
        
        if not self.email:
            raise UserError(_('Email address is required for verification.'))
        
        try:
            template = self.env.ref('auth_signup_email_verification.mail_template_email_verification')
            
            # Get partner's language or fallback to English
            partner_lang = self.lang or 'en_US'
            
            # Verify language exists in installed languages
            installed_langs = [code for code, _ in self.env['res.lang'].get_installed()]
            if partner_lang not in installed_langs:
                _logger.warning("Partner language %s not installed, falling back to en_US", partner_lang)
                partner_lang = 'en_US'
            
            # Send email using sudo to avoid using current user's email
            # This prevents showing wrong sender name when another user is logged in
            template.sudo().with_context(lang=partner_lang).send_mail(
                self.id,
                force_send=True,
                raise_exception=True,
                email_values={
                    'email_from': self.env.company.email or 'noreply@example.com',
                }
            )
            
            _logger.info("Verification email sent successfully to: %s in language: %s", self.email, partner_lang)
        except Exception as e:
            _logger.error("Failed to send verification email to %s: %s", self.email, str(e))
            raise UserError(_('Failed to send verification email. Please try again.'))

    def get_verification_url(self):
        """
        Get verification URL for email templates with subdomain support
        REPLACES the subdomain instead of prepending it
        """
        self.ensure_one()
        
        # Use Odoo's official token generation
        token = self._generate_signup_token()
        
        # Get base URL
        base_url = self.get_base_url()
        
        _logger.info("=== VERIFICATION URL GENERATION ===")
        _logger.info("Original base_url: %s", base_url)
        _logger.info("Stored signup_subdomain: %s", self.signup_subdomain)
        
        # If subdomain was stored during signup, REPLACE the current subdomain
        if self.signup_subdomain:
            from urllib.parse import urlparse, urlunparse
            
            try:
                parsed = urlparse(base_url)
                hostname = parsed.hostname or parsed.netloc.split(':')[0]
                hostname_parts = hostname.split('.')
                
                _logger.info("Hostname parts: %s", hostname_parts)
                
                # Check if current subdomain matches the stored one
                if len(hostname_parts) >= 2:
                    current_subdomain = hostname_parts[0]
                    
                    if current_subdomain != self.signup_subdomain:
                        # REPLACE the first part (subdomain) with the stored subdomain
                        # Example: th.mrbur.local -> my.mrbur.local
                        hostname_parts[0] = self.signup_subdomain
                        new_hostname = '.'.join(hostname_parts)
                        
                        _logger.info("Replacing subdomain '%s' with '%s'", current_subdomain, self.signup_subdomain)
                        _logger.info("New hostname: %s", new_hostname)
                        
                        # Handle port if present
                        netloc = new_hostname
                        if parsed.port:
                            netloc = f"{new_hostname}:{parsed.port}"
                        
                        # Reconstruct URL with replaced subdomain
                        base_url = urlunparse((
                            parsed.scheme,
                            netloc,
                            parsed.path,
                            parsed.params,
                            parsed.query,
                            parsed.fragment
                        ))
                        
                        _logger.info("✓ Modified verification URL: %s", base_url)
                    else:
                        _logger.info("Subdomain already matches: %s", self.signup_subdomain)
                else:
                    _logger.warning("Hostname has less than 2 parts, cannot replace subdomain")
                    
            except Exception as e:
                _logger.error("Error processing subdomain in URL: %s", str(e))
                # Fall back to original base_url if there's an error
        
        # Generate custom verification URL
        verification_url = f"{base_url}/auth/verify/email?token={token}"
        
        _logger.info("Final verification URL: %s", verification_url)
        _logger.info("===================================")
        return verification_url

    def complete_email_verification(self):
        """Complete email verification and mark as verified"""
        self.ensure_one()
        
        if self.email_verified:
            raise UserError(_('Email has already been verified.'))
        
        # Mark email as verified
        self.write({'email_verified': True})
        
        _logger.info("Email verification completed for: %s", self.email)
        return True

    @api.model
    def create_partner_for_signup(self, email, user_data):
        """Create partner for email verification signup with company/individual support"""
        # EXTRACT AND STORE SUBDOMAIN
        subdomain = user_data.pop('signup_subdomain', None)
        if subdomain:
            _logger.info("Subdomain extracted from user_data: %s", subdomain)
        else:
            _logger.warning("No subdomain found in user_data")
        
        # Check if partner already exists (check by contact email for companies)
        contact_email = email if user_data.get('signup_company_type', 'person') != 'company' else email
        existing_partner = self.search([('email', '=', contact_email)], limit=1)
        if existing_partner:
            if existing_partner.user_ids:
                raise UserError(_('A user with this email already exists.'))
            # Update existing partner with subdomain
            existing_partner.write({'signup_subdomain': subdomain})
            existing_partner.signup_prepare_with_verification(user_data)
            return existing_partner
        
        # Determine signup type
        company_type = user_data.get('signup_company_type', 'person')
        _logger.info("company_type from user_data: %s", company_type)
        
        if company_type == 'company':
            # Company signup - simplified: create only company record with single email
            company_name = user_data.get('name', 'Company')  # Company name from form
            company_email = email  # Single email for the company (no separate contact)
            
            # Company record with all fields INCLUDING SUBDOMAIN
            company_vals = {
                'name': company_name, 
                'is_company': True, 
                'email': company_email,  # Single company email
                'lang': user_data.get('lang', 'en_US'),
                'company_id': self.env.company.id,
                'customer_rank': 1,  # Mark as customer
                'signup_subdomain': subdomain,  # STORE SUBDOMAIN
            }
            
            # ADD OCCUPATION/FUNCTION if present
            if user_data.get('function'):
                company_vals['function'] = user_data.get('function')
            
            # Process dynamic fields from configuration - all go to company
            try:
                all_configs = self.env['ir.config_parameter'].sudo().get_param(
                    'auth_signup_email_verification.all_field_configurations', '{}'
                )
                import json
                dynamic_fields = json.loads(all_configs) if all_configs else {}
                
                # Process all dynamic fields from all models
                for model_name, field_names in dynamic_fields.items():
                    for field_name in field_names:
                        field_value = user_data.get(field_name)
                        if field_value:
                            # DEBUG: Special logging for many2one fields like country_id
                            if field_name == 'country_id':
                                _logger.info("  - COUNTRY_ID DEBUG: raw value = %s (type: %s)", field_value, type(field_value))
                            
                            company_vals[field_name] = field_value
                            _logger.info("  - Added dynamic field: %s = %s", field_name, field_value)
                                
            except Exception as e:
                _logger.warning("Error processing dynamic fields: %s", str(e))
            
            # Create single company partner
            company_partner = self.create(company_vals)
            _logger.info("Created company partner: %s (ID: %s) with language: %s and subdomain: %s", 
                        company_partner.name, company_partner.id, company_partner.lang, company_partner.signup_subdomain)
            
            # Prepare company for verification (user will be created for company directly)
            company_partner.signup_prepare_with_verification(user_data)
            _logger.info("Returning company partner for user creation")
            return company_partner
            
        else:
            # For individual signup: create individual partner
            _logger.info("Creating INDIVIDUAL partner:")
            _logger.info("  - name: %s", user_data.get('name'))
            _logger.info("  - subdomain: %s", subdomain)
            
            partner = self.create({
                'name': user_data.get('name'),
                'email': email,
                'is_company': False,
                'customer_rank': 1,  # Mark as customer
                'lang': user_data.get('lang', 'en_US'),  # Apply language to individual
                'company_id': self.env.company.id,  # Set current Odoo company
                'signup_subdomain': subdomain,  # STORE SUBDOMAIN
                'function': user_data.get('function'),  # ADD OCCUPATION
            })
            _logger.info("Created individual partner: %s (ID: %s) with language: %s, subdomain: %s, occupation: %s", 
                        partner.name, partner.id, partner.lang, partner.signup_subdomain, partner.function)
            
            # Prepare for verification
            partner.signup_prepare_with_verification(user_data)
            return partner