"""
Geo Redirect Module - controllers/main.py
Provides a helper service that ANY controller can call to check geo redirects.
This way the geo redirect module has NO dependencies and can work with anything.
"""
import logging
import geoip2.database
import geoip2.errors
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class GeoRedirectService:
    """
    Service class that provides geo redirect functionality.
    Other controllers can instantiate this and call check_redirect().
    """
    
    @staticmethod
    def get_client_ip():
        """Get the real client IP address"""
        forwarded_for = request.httprequest.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.httprequest.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.httprequest.remote_addr
    
    @staticmethod
    def get_country_from_ip(ip_address):
        """Get country code from IP address using GeoLite2 database"""
        try:
            db_path = 'C:/geoip/GeoLite2-Country.mmdb'

            with geoip2.database.Reader(db_path) as reader:
                response = reader.country(ip_address)
                country_code = response.country.iso_code
                return country_code
                
        except geoip2.errors.AddressNotFoundError:
            _logger.warning(f'IP address {ip_address} not found in GeoIP database')
            return None
        except FileNotFoundError:
            _logger.error('GeoLite2 database file not found.')
            return None
        except Exception as e:
            _logger.error(f'Error detecting country from IP: {str(e)}')
            return None
    
    @staticmethod
    def get_redirect_url(country_code):
        """Get the redirect URL for a country code"""
        if not country_code:
            return None
        
        try:
            RedirectConfig = request.env['geo.redirect.config'].sudo()
            config = RedirectConfig.search([
                ('country_code', '=', country_code),
                ('active', '=', True)
            ], limit=1)
            
            if config:
                return config.redirect_url
        except Exception as e:
            _logger.error(f'Error getting redirect URL: {e}')
        
        return None
    
    @staticmethod
    def check_redirect(**kwargs):
        """
        Check if geo redirect is needed and return redirect response if yes.
        Returns None if no redirect is needed.
        
        Only redirects FROM www.mrbur.shop to country-specific domains.
        Country-specific domains never redirect (they're the destination).
        
        Usage in any controller:
            from odoo.addons.geo_redirect.controllers.main import GeoRedirectService
            
            @http.route('/', ...)
            def your_method(self, **kwargs):
                redirect = GeoRedirectService.check_redirect(**kwargs)
                if redirect:
                    return redirect
                # ... your normal logic
        """
        # _logger.info('=== GEO REDIRECT CHECK ===')
        
        # Skip if user opted out
        if kwargs.get('no_redirect'):
            # _logger.info('Skipping - user opted out')
            return None
        
        current_host = request.httprequest.host
        # _logger.info(f'Current host: {current_host}')
        
        # ONLY redirect from www.mrbur.shop
        # If we're already on a country-specific domain, skip redirect
        if current_host != 'www.mrbur.shop':
            _logger.info(f'Not on www.mrbur.shop, skipping redirect')
            return None
        
        ip_address = GeoRedirectService.get_client_ip()
        country_code = GeoRedirectService.get_country_from_ip(ip_address)
        
        # _logger.info(f'IP: {ip_address}, Country: {country_code}')
        
        redirect_url = GeoRedirectService.get_redirect_url(country_code)
        
        if redirect_url:
            from urllib.parse import urlparse
            target_host = urlparse(redirect_url).netloc
            
            # This should always be true since we're on www.mrbur.shop
            if target_host != current_host:
                full_redirect_url = redirect_url.rstrip('/') + '/'
                # _logger.info(f'REDIRECTING to {full_redirect_url}')
                
                return request.make_response(f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <title>Redirecting...</title>
                        <script type="text/javascript">
                            window.location.replace("{full_redirect_url}");
                        </script>
                    </head>
                    <body>
                        <p>Redirecting to your local store...</p>
                        <p>If you are not redirected, <a href="{full_redirect_url}">click here</a>.</p>
                    </body>
                    </html>
                ''')
        
        return None


class GeoRedirectController(http.Controller):
    """Test endpoints for geo redirect"""
    
    @http.route(['/geo/test'], type='http', auth='public')
    def test_geo(self, **kwargs):
        """Test geolocation detection"""
        ip = GeoRedirectService.get_client_ip()
        country = GeoRedirectService.get_country_from_ip(ip)
        redirect_url = GeoRedirectService.get_redirect_url(country)
        
        return f"""
        <h1>Geo Test</h1>
        <p>IP: {ip}</p>
        <p>Country: {country}</p>
        <p>Redirect URL: {redirect_url}</p>
        <p>Current host: {request.httprequest.host}</p>
        <p><a href="/">Test Redirect (Go to homepage)</a></p>
        """