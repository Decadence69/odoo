# -*- coding: utf-8 -*-

import logging
import json
import werkzeug
from werkzeug.urls import url_encode

from odoo import http, _
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.exceptions import UserError
from odoo.http import request
from markupsafe import Markup

_logger = logging.getLogger(__name__)


class AuthSignupEmailVerification(AuthSignupHome):
    """Enhanced signup controller with email verification using Odoo's official signup system"""

    def _get_current_subdomain(self):
        """Extract subdomain from current request"""
        try:
            if hasattr(request, 'httprequest'):
                host = request.httprequest.host
                # Split host to get subdomain
                # Example: my.mrbur.shop -> ['my', 'mrbur', 'shop']
                parts = host.split('.')
                if len(parts) > 2:
                    # Return subdomain (e.g., 'my')
                    return parts[0]
        except Exception as e:
            _logger.warning("Could not extract subdomain: %s", str(e))
        return None

    def get_auth_signup_qcontext(self):
        """Enhanced qcontext with company toggle setting and custom fields"""
        # Get standard context from parent
        qcontext = super().get_auth_signup_qcontext()
        
        # Add our custom fields that get filtered out by SIGN_UP_REQUEST_PARAMS
        if 'company_type' in request.params:
            qcontext['company_type'] = request.params['company_type']
        if 'contact_name' in request.params:
            qcontext['contact_name'] = request.params['contact_name']
        if 'company_email' in request.params:
            qcontext['company_email'] = request.params['company_email']
        
        # Add our custom setting context with debug logging
        # NOTE: When boolean settings are unchecked in Odoo, the parameter gets DELETED from database
        # For new installations (no parameter exists), we default to True (enabled)
        toggle_param = request.env['ir.config_parameter'].sudo().get_param(
            'auth_signup_email_verification.company_toggle'
        )
        # If parameter doesn't exist (new installation), default to True (enabled)  
        # If parameter exists, check if it's 'True' or 'False'
        if toggle_param is None:
            company_toggle_enabled = True  # Default enabled for new installations
        else:
            company_toggle_enabled = toggle_param == 'True'
        
        qcontext['company_toggle_enabled'] = company_toggle_enabled
        
        # Add dynamic company fields if toggle is enabled
        if company_toggle_enabled:
            # Get current session/request language (not website default!)
            current_lang = None
            
            # Priority order for language detection:
            # 1. Website context language (from language switching)
            # 2. Current session language
            # 3. Request context language  
            # 4. Environment context language
            # 5. Fallback to English
            
            # Check if website module is available and get current website language
            if hasattr(request, 'website') and request.website:
                # Get the current website context language (from language switcher)
                website_context = getattr(request, 'context', {})
                if website_context.get('lang'):
                    current_lang = website_context.get('lang')
                elif hasattr(request.website, 'get_current_website_language'):
                    current_lang = request.website.get_current_website_language()
                else:
                    # Fallback to checking the request environment with website context
                    current_lang = request.env.context.get('lang')
            elif hasattr(request, 'session') and request.session.get('lang'):
                current_lang = request.session.get('lang')
            elif request.context.get('lang'):
                current_lang = request.context.get('lang')
            elif request.env.context.get('lang'):
                current_lang = request.env.context.get('lang')
            elif hasattr(request, 'httprequest') and request.httprequest.args.get('lang'):
                # Check for lang parameter in URL
                current_lang = request.httprequest.args.get('lang')
            else:
                current_lang = 'en_US'  # Default to English

            # Get selected dynamic fields from configuration with proper language context
            settings_model = request.env['res.config.settings'].with_context(lang=current_lang)
            selected_fields = settings_model.get_selected_company_fields()
            qcontext['dynamic_company_fields'] = selected_fields

            # Add dynamic field values from request params
            for field_info in selected_fields:
                field_name = field_info.get('name')
                if field_name in request.params:
                    qcontext[field_name] = request.params[field_name]
        else:
            qcontext['dynamic_company_fields'] = []
        
        return qcontext

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """Override default signup to add email verification step"""
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        # If there's a token, this might be a standard signup completion
        # Let the parent class handle it (fallback to original behavior)
        if qcontext.get('token'):
            return super(AuthSignupEmailVerification, self).web_auth_signup(*args, **kw)

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                # Optional ReCaptcha verification (if method exists)
                try:
                    if hasattr(request.env['ir.http'], '_verify_request_recaptcha_token'):
                        if not request.env['ir.http']._verify_request_recaptcha_token('signup'):
                            raise UserError(_("Suspicious activity detected by Google reCaptcha."))
                except Exception as e:
                    _logger.warning("ReCaptcha verification skipped: %s", str(e))

                # Get signup data
                email = qcontext.get('login')
                name = qcontext.get('name')
                password = qcontext.get('password')
                
                # Check if company toggle is enabled in settings
                toggle_param = request.env['ir.config_parameter'].sudo().get_param(
                    'auth_signup_email_verification.company_toggle'
                )
                # Handle default for new installations
                if toggle_param is None:
                    company_toggle_enabled = True  # Default enabled for new installations
                else:
                    company_toggle_enabled = toggle_param == 'True'
                
                # Only get company_type if toggle is enabled, otherwise default to individual
                if company_toggle_enabled:
                    company_type = qcontext.get('company_type', 'person')  # Default to individual
                    contact_name = qcontext.get('contact_name')
                    company_email = qcontext.get('company_email')
                else:
                    company_type = 'person'  # Force individual if toggle is disabled
                    contact_name = None
                    company_email = None
                
                if not email or not name or not password:
                    raise UserError(_("Please fill in all required fields."))
                
                # Additional validation for company type (only if toggle is enabled)
                if company_toggle_enabled and company_type == 'company':
                    if not name:
                        raise UserError(_("Company name is required for company accounts."))
                
                if password != qcontext.get('confirm_password'):
                    raise UserError(_("Passwords do not match; please retype them."))

                # Check if user already exists
                existing_user = request.env['res.users'].sudo().search([
                    ('login', '=', email)
                ], limit=1)
                
                if existing_user:
                    qcontext['error'] = _("Another user is already registered using this email address.")
                    return self._render_signup_page(qcontext)

                # Handle signup with email verification
                return self._handle_signup_with_verification(qcontext)
                
            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                _logger.warning("%s", e)
                qcontext['error'] = _("Could not create a new account.") + Markup('<br/>') + str(e)

        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search([
                ('email', '=', qcontext.get('signup_email')), 
                ('state', '!=', 'new')
            ], limit=1)
            if user:
                return request.redirect('/web/login?%s' % url_encode({'login': user.login, 'redirect': '/web'}))

        return self._render_signup_page(qcontext)

    def _render_signup_page(self, qcontext):
        """Render signup page with proper headers"""
        response = request.render('auth_signup.signup', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    def _handle_signup_with_verification(self, qcontext):
        """Handle signup with email verification using official res.partner"""
        email = qcontext.get('login')
        company_type = qcontext.get('company_type', 'person')
        contact_name = qcontext.get('contact_name')
        
        # CAPTURE SUBDOMAIN
        subdomain = self._get_current_subdomain()
        
        # Prepare user data based on account type
        if company_type == 'company':
            # For company accounts - simplified single email approach
            user_data = {
                'name': qcontext.get('name'),  # Company name
                'login': email,  # Company email (single email)
                'password': qcontext.get('password'),
                'is_company': True,  # Company account
            }
        else:
            # For individual accounts
            user_data = {
                'name': qcontext.get('name'),
                'login': email,
                'password': qcontext.get('password'),
                'is_company': False,  # Individual person
            }
        
        # ADD SUBDOMAIN TO USER DATA
        if subdomain:
            user_data['signup_subdomain'] = subdomain
        
        # ADD FUNCTION/OCCUPATION TO USER DATA
        if function:
            user_data['function'] = function
        else:
            _logger.warning("✗ No function/occupation found to add to user_data")
        
        # Get current website language properly
        supported_lang_codes = [code for code, _ in request.env['res.lang'].get_installed()]
        
        # Try multiple sources for current language
        lang = (
            request.context.get('lang') or          # Context language
            request.env.context.get('lang') or     # Environment language  
            (hasattr(request, 'website') and request.website.default_lang_id.code) or  # Website language
            'en_US'  # Fallback to English
        )
        
        # Ensure language is supported (check exact match first, then fallback)
        if lang in supported_lang_codes:
            user_data['lang'] = lang
        elif lang and '_' in lang:
            # Try language without country code (e.g., 'fr' from 'fr_FR')
            lang_short = lang.split('_')[0]
            # Look for any language that starts with the short code
            matching_lang = next((code for code in supported_lang_codes if code.startswith(lang_short + '_')), None)
            if matching_lang:
                user_data['lang'] = matching_lang
            else:
                user_data['lang'] = 'en_US'  # Fallback to English
        else:
            user_data['lang'] = 'en_US'  # Fallback to English
        
        # Store additional data for later use
        user_data['signup_company_type'] = company_type
        
        # ADD DYNAMIC COMPANY FIELDS to user_data
        if company_type == 'company':
            # Get selected dynamic fields from configuration with proper language context
            current_lang = user_data.get('lang', 'en_US')  # Use detected language from user_data
            settings_model = request.env['res.config.settings'].with_context(lang=current_lang)
            selected_fields = settings_model.get_selected_company_fields()
            
            # Add dynamic field values from qcontext to user_data
            for field_info in selected_fields:
                field_name = field_info.get('name')
                field_type = field_info.get('type')
                
                # Handle binary/image fields (file uploads)
                if field_type in ['binary', 'image'] and hasattr(request.httprequest, 'files'):
                    uploaded_file = request.httprequest.files.get(field_name)
                    if uploaded_file and uploaded_file.filename:
                        try:
                            # Read file data and encode as base64 for Odoo binary fields
                            import base64
                            file_data = uploaded_file.read()
                            encoded_data = base64.b64encode(file_data).decode('utf-8')
                            user_data[field_name] = encoded_data
                            
                            # Store filename separately if needed
                            if field_type == 'binary':
                                filename_field = field_name + '_filename'
                                user_data[filename_field] = uploaded_file.filename
                            
                        except Exception as e:
                            _logger.error("Error processing file upload for %s: %s", field_name, str(e))
                            continue
                
                # Handle regular fields (non-binary) with proper type conversion
                elif field_name in qcontext and qcontext[field_name]:
                    raw_value = qcontext[field_name]
                    
                    # Convert based on field type
                    if field_type == 'many2one':
                        # Convert string ID to integer for many2one fields
                        try:
                            user_data[field_name] = int(raw_value) if raw_value and str(raw_value).isdigit() else False
                        except (ValueError, TypeError):
                            user_data[field_name] = False
                    elif field_type == 'many2many':
                        # Convert to list of integers for many2many fields
                        if isinstance(raw_value, list):
                            user_data[field_name] = [(6, 0, [int(x) for x in raw_value if str(x).isdigit()])]
                        else:
                            user_data[field_name] = [(6, 0, [int(raw_value)])] if str(raw_value).isdigit() else [(6, 0, [])]
                    elif field_type == 'boolean':
                        # Convert to boolean
                        user_data[field_name] = bool(raw_value and raw_value not in ('false', 'False', '0'))
                    elif field_type == 'integer':
                        # Convert to integer
                        try:
                            user_data[field_name] = int(raw_value) if raw_value else 0
                        except (ValueError, TypeError):
                            user_data[field_name] = 0
                    elif field_type == 'float':
                        # Convert to float
                        try:
                            user_data[field_name] = float(raw_value) if raw_value else 0.0
                        except (ValueError, TypeError):
                            user_data[field_name] = 0.0
                    else:
                        # Keep as string for char, text, selection, date, datetime fields
                        user_data[field_name] = str(raw_value) if raw_value else False
                    
        # Create partner and initiate verification using official signup system
        partner = request.env['res.partner'].sudo().create_partner_for_signup(email, user_data)
        
        # Show verification pending page
        return self._render_verification_pending(email)

    def _render_verification_pending(self, email):
        """Render verification pending page"""
        # Get verification validity hours from settings
        verification_hours = request.env['ir.config_parameter'].sudo().get_param(
            'auth_signup_email_verification.verification_validity_hours', '144'
        )
        
        values = {
            'email': email,
            'company_name': request.env.company.name,
            'verification_hours': verification_hours,
        }
        
        response = request.render('auth_signup_email_verification.email_verification_pending', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    @http.route('/auth/verify/email', type='http', auth='public', website=True, sitemap=False)
    def verify_email(self, token=None, **kw):
        """Verify email address using Odoo's official signup token"""
        if not token:
            _logger.warning("Email verification attempted without token")
            return self._render_verification_error(_('Invalid verification link.'))
        
        # IMPORTANT: If user is already logged in, log them out first
        # This prevents session conflicts when verifying a different account
        if request.session.uid:
            request.session.logout(keep_db=True)
        
        try:
            # Use Odoo's official token verification
            partner = request.env['res.partner'].sudo()._signup_retrieve_partner(
                token, check_validity=True, raise_exception=False
            )
            
            if not partner:
                _logger.warning("Token verification failed - no partner found for token")
                return self._render_verification_error(
                    _('Verification link has expired or is invalid. Please try signing up again.')
                )
            
            # Check if user already exists
            existing_user = request.env['res.users'].sudo().search([
                ('login', '=', partner.email)
            ], limit=1)
            
            if existing_user:
                credential = {
                    'login': existing_user.login,
                    'password': False,  # Skip password for existing users
                    'type': 'password'
                }
                try:
                    request.session.authenticate(request.db, credential)
                    return request.redirect('/my')
                except:
                    # If auth fails, redirect to login
                    return request.redirect('/web/login?message=account_exists')
            
            # Prepare signup data (already cleaned when stored)
            signup_data = partner.signup_user_data or {}
            
            # Complete verification using official signup system (following Odoo's standard pattern)
            result = request.env['res.users'].sudo().signup(
                signup_data,
                token=token
            )
            
            # Handle both return formats
            if result and len(result) == 2:
                # Format: (login, password)
                login, password = result
            elif result and len(result) == 3:
                # Format: (db, login, password)
                _, login, password = result
            else:
                _logger.error("Signup returned unexpected format: %s", result)
                return self._render_verification_error(
                    _('Failed to create user account. Please contact support.')
                )
            
            if login and password:
                # Commit transaction before authentication (as per Odoo's standard auth_signup)
                request.env.cr.commit()
                
                # Use Odoo's standard authentication format
                credential = {'login': login, 'password': password, 'type': 'password'}
                request.session.authenticate(request.db, credential)
                
                # Redirect directly to portal after successful login
                return request.redirect('/my')
            else:
                _logger.error("Signup returned no result")
                return self._render_verification_error(
                    _('Failed to create user account. Please contact support.')
                )
            
        except Exception as e:
            _logger.error("Error in email verification: %s - %s", type(e).__name__, str(e))
            return self._render_verification_error(
                _('An error occurred during verification. Please try signing up again.')
            )

    def _render_verification_error(self, error_message):
        """Render verification error page"""
        values = {'error_msg': error_message}
        response = request.render('auth_signup_email_verification.email_verification_error', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    def _render_verification_success(self, partner):
        """Render verification success page"""
        values = {
            'user_name': partner.name,
            'email': partner.email,
            'company_name': request.env.company.name,
            'redirect_url': '/my',  # Standard portal redirect
        }
        
        response = request.render('auth_signup_email_verification.email_verification_success', values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    @http.route('/auth/resend/verification', type='http', auth='public', website=True, sitemap=False)
    def resend_verification(self, email=None, **kw):
        """Resend verification email"""
        if not email:
            return request.redirect('/web/signup')
        
        try:
            # Find partner with pending verification
            partner = request.env['res.partner'].sudo().search([
                ('email', '=', email),
                ('signup_type', '=', 'signup'),
                ('email_verified', '=', False)
            ], limit=1)
            
            if not partner:
                return self._render_verification_error(
                    _('No pending verification found for this email.')
                )
            
            # Resend verification email
            partner._send_verification_email()
            
            return self._render_verification_pending(email)
            
        except Exception as e:
            _logger.error("Error resending verification email: %s", str(e))
            return self._render_verification_error(
                _('Failed to resend verification email. Please try again.')
            )

    @http.route('/auth/get_model_fields', type='json', auth='user', methods=['POST'])
    def get_model_fields(self, model_name=None, **kw):
        """AJAX endpoint to get fields for a selected model"""
        try:
            if not model_name:
                return []
            
            # Use the same method from res.config.settings
            settings = request.env['res.config.settings']
            fields_list = settings.get_model_fields(model_name)
            
            return fields_list
        except Exception as e:
            _logger.error("Error fetching model fields for %s: %s", model_name, str(e))
            return []

    @http.route('/signup/get_field_options', type='json', auth='public', methods=['POST'], website=True, csrf=False)
    def get_field_options(self, field_name, model_name, parent_field=None, parent_value=None, **kw):
        """Get options for a dependent field (e.g., states for a selected country)"""
        try:
            # Get the model and field info
            model = request.env[model_name].sudo()
            field_obj = model._fields.get(field_name)
            
            if not field_obj or field_obj.type != 'many2one':
                return {'error': 'Invalid field or not a many2one field'}
            
            relation_model_name = field_obj.comodel_name
            relation_model = request.env[relation_model_name].sudo()
            
            # Build domain based on parent field selection
            domain = []
            
            # Add active filter if available
            if 'active' in relation_model._fields:
                domain.append(('active', '=', True))
            
            # Add parent field filter if provided
            if parent_field and parent_value:
                try:
                    parent_value_int = int(parent_value)  # Convert to integer for many2one
                    domain.append((parent_field, '=', parent_value_int))
                except ValueError:
                    # If conversion fails, use string value
                    domain.append((parent_field, '=', parent_value))
            
            # Get the best ordering field
            order_field = 'id'  # Safe fallback
            for potential_field in ['name', 'title', 'code', 'sequence']:
                if potential_field in relation_model._fields:
                    field_def = relation_model._fields[potential_field]
                    if getattr(field_def, 'store', True) and not getattr(field_def, 'compute', None):
                        order_field = potential_field
                        break
            
            # Search records
            try:
                records = relation_model.search(domain, order=f'{order_field} asc')
            except Exception:
                records = relation_model.search(domain)
            
            # Build options list
            options = []
            for record in records:
                display_value = str(record.id)  # Safe fallback
                
                # Try different display options
                for display_attr in ['display_name', 'name', 'title', 'code']:
                    try:
                        if hasattr(record, display_attr):
                            value = getattr(record, display_attr, None)
                            if value:
                                display_value = str(value)
                                break
                    except Exception:
                        continue
                
                options.append({
                    'id': record.id,
                    'name': display_value
                })
            
            return {
                'options': options,
                'field_name': field_name
            }
            
        except Exception as e:
            _logger.error(f"Error getting field options: {e}")
            return {'error': str(e)}