import re
from odoo import http, _
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
# Import the email verification controller
from odoo.addons.auth_signup_email_verification.controllers.main import AuthSignupEmailVerification
import logging

_logger = logging.getLogger(__name__)
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

class DentistAuthSignupHome(AuthSignupEmailVerification):
    """
    Extend the email verification controller instead of base AuthSignupHome
    This ensures compatibility with email verification flow
    """

    def get_auth_signup_qcontext(self):
        """Override to include function field in qcontext"""
        qcontext = super(DentistAuthSignupHome, self).get_auth_signup_qcontext()
        
        # Add function/occupation from request params
        function = request.params.get('function')
        if function:
            qcontext['function'] = function
            _logger.info('Added function/occupation to qcontext: %s', function)
        
        return qcontext

    def _handle_signup_with_verification(self, qcontext):
        """
        Override the email verification handler to include occupation in user_data
        This ensures occupation is saved even with email verification
        """
        email = qcontext.get('login')
        company_type = qcontext.get('company_type', 'person')
        contact_name = qcontext.get('contact_name')
        
        # Capture subdomain (from parent class)
        subdomain = self._get_current_subdomain()
        _logger.info("=== SIGNUP WITH OCCUPATION ===")
        _logger.info("Captured subdomain: %s", subdomain)
        _logger.info("Full host: %s", request.httprequest.host if hasattr(request, 'httprequest') else 'N/A')
        
        # Get occupation/function from qcontext
        function = qcontext.get('function')
        _logger.info("Occupation/Function: %s", function)
        
        # Check if company toggle is enabled in settings
        toggle_param = request.env['ir.config_parameter'].sudo().get_param(
            'auth_signup_email_verification.company_toggle'
        )
        if toggle_param is None:
            company_toggle_enabled = True
        else:
            company_toggle_enabled = toggle_param == 'True'
        
        if company_toggle_enabled:
            company_type = qcontext.get('company_type', 'person')
        else:
            company_type = 'person'
        
        # Prepare user data based on account type
        if company_type == 'company':
            user_data = {
                'name': qcontext.get('name'),
                'login': email,
                'password': qcontext.get('password'),
                'is_company': True,
            }
        else:
            user_data = {
                'name': qcontext.get('name'),
                'login': email,
                'password': qcontext.get('password'),
                'is_company': False,
            }
        
        # ADD SUBDOMAIN to user_data
        if subdomain:
            user_data['signup_subdomain'] = subdomain
        
        # ADD OCCUPATION/FUNCTION to user_data
        if function:
            user_data['function'] = function
            _logger.info("Added occupation to user_data: %s", function)
        
        # Get current website language properly
        supported_lang_codes = [code for code, _ in request.env['res.lang'].get_installed()]
        
        lang = (
            request.context.get('lang') or
            request.env.context.get('lang') or
            (hasattr(request, 'website') and request.website.default_lang_id.code) or
            'en_US'
        )
        
        if lang in supported_lang_codes:
            user_data['lang'] = lang
        elif lang and '_' in lang:
            lang_short = lang.split('_')[0]
            matching_lang = next((code for code in supported_lang_codes if code.startswith(lang_short + '_')), None)
            if matching_lang:
                user_data['lang'] = matching_lang
            else:
                user_data['lang'] = 'en_US'
        else:
            user_data['lang'] = 'en_US'
        
        user_data['signup_company_type'] = company_type
        
        # ADD DYNAMIC COMPANY FIELDS to user_data (if applicable)
        if company_type == 'company':
            current_lang = user_data.get('lang', 'en_US')
            settings_model = request.env['res.config.settings'].with_context(lang=current_lang)
            selected_fields = settings_model.get_selected_company_fields()
            
            _logger.info("=== ADDING DYNAMIC FIELDS ===")
            _logger.info("Selected fields: %s", [f.get('name') for f in selected_fields])
            
            for field_info in selected_fields:
                field_name = field_info.get('name')
                field_type = field_info.get('type')
                
                if field_type in ['binary', 'image'] and hasattr(request.httprequest, 'files'):
                    uploaded_file = request.httprequest.files.get(field_name)
                    if uploaded_file and uploaded_file.filename:
                        try:
                            import base64
                            file_data = uploaded_file.read()
                            encoded_data = base64.b64encode(file_data).decode('utf-8')
                            user_data[field_name] = encoded_data
                            
                            if field_type == 'binary':
                                filename_field = field_name + '_filename'
                                user_data[filename_field] = uploaded_file.filename
                            
                            _logger.info("Added binary field: %s = [file: %s, size: %d bytes]", 
                                       field_name, uploaded_file.filename, len(file_data))
                        except Exception as e:
                            _logger.error("Error processing file upload for %s: %s", field_name, str(e))
                            continue
                
                elif field_name in qcontext and qcontext[field_name]:
                    raw_value = qcontext[field_name]
                    
                    if field_type == 'many2one':
                        try:
                            user_data[field_name] = int(raw_value) if raw_value and str(raw_value).isdigit() else False
                        except (ValueError, TypeError):
                            user_data[field_name] = False
                    elif field_type == 'many2many':
                        if isinstance(raw_value, list):
                            user_data[field_name] = [(6, 0, [int(x) for x in raw_value if str(x).isdigit()])]
                        else:
                            user_data[field_name] = [(6, 0, [int(raw_value)])] if str(raw_value).isdigit() else [(6, 0, [])]
                    elif field_type == 'boolean':
                        user_data[field_name] = bool(raw_value and raw_value not in ('false', 'False', '0'))
                    elif field_type == 'integer':
                        try:
                            user_data[field_name] = int(raw_value) if raw_value else 0
                        except (ValueError, TypeError):
                            user_data[field_name] = 0
                    elif field_type == 'float':
                        try:
                            user_data[field_name] = float(raw_value) if raw_value else 0.0
                        except (ValueError, TypeError):
                            user_data[field_name] = 0.0
                    else:
                        user_data[field_name] = str(raw_value) if raw_value else False
                    
                    _logger.info("Added dynamic field: %s (%s) = %s", field_name, field_type, user_data[field_name])
        
        _logger.info("=== FINAL USER DATA WITH OCCUPATION ===")
        _logger.info("user_data: %s", user_data)
        _logger.info("=======================================")
        
        # Create partner and initiate verification using official signup system
        partner = request.env['res.partner'].sudo().create_partner_for_signup(email, user_data)
        
        # Show verification pending page
        return self._render_verification_pending(email)

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        """
        Override signup route to handle occupation field and email verification
        """
        # 1) HTML5 does most checks, but keep a light server-side check
        login = (kw or {}).get('login')
        if login and not EMAIL_RE.match(login):
            qcontext = self.get_auth_signup_qcontext()
            qcontext['error'] = _("Please enter a valid email address.")
            return http.request.render('auth_signup.signup', qcontext)

        # 2) Call parent (email verification controller) which handles the verification flow
        # The occupation will be saved in user_data via _handle_signup_with_verification
        res = super().web_auth_signup(*args, **kw)

        # 3) After verification completes, redirect to /shop instead of /my
        # Note: This only applies after email verification is complete
        try:
            if getattr(res, 'status_code', None) in (301, 302, 303):
                loc = res.headers.get('Location')
                # Redirect to /shop after successful verification
                if loc and '/my' in loc and 'redirect=' not in loc:
                    res.headers['Location'] = '/shop'
        except Exception:
            pass

        return res