import logging
import geoip2.database
import geoip2.errors
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class GeoRedirectController(http.Controller):
    
    def _get_client_ip(self):
        """Get the real client IP address"""
        # Check for forwarded IP first (when behind proxy/load balancer)
        forwarded_for = request.httprequest.headers.get('X-Forwarded-For')
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, get the first one
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.httprequest.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.httprequest.remote_addr
    
    def _get_country_from_ip(self, ip_address):
        """Get country code from IP address using GeoLite2 database"""
        try:
            # Path to GeoLite2 database file
            # Download from: https://dev.maxmind.com/geoip/geoip2/geolite2/
            db_path = 'C:/geoip/GeoLite2-Country.mmdb'
            
            # For local testing, skip localhost IPs
            if ip_address in ['127.0.0.1', 'localhost', '::1']:
                _logger.info('Localhost detected, skipping geo redirect')
                return None
            
            with geoip2.database.Reader(db_path) as reader:
                response = reader.country(ip_address)
                country_code = response.country.iso_code
                _logger.info(f'Detected country {country_code} for IP {ip_address}')
                return country_code
                
        except geoip2.errors.AddressNotFoundError:
            _logger.warning(f'IP address {ip_address} not found in GeoIP database')
            return None
        except FileNotFoundError:
            _logger.error('GeoLite2 database file not found. Please download and configure.')
            return None
        except Exception as e:
            _logger.error(f'Error detecting country from IP: {str(e)}')
            return None
    
    def _get_redirect_url(self, country_code):
        """Get the redirect URL for a country code"""
        if not country_code:
            return None
        
        # Get active redirect configurations
        RedirectConfig = request.env['geo.redirect.config'].sudo()
        config = RedirectConfig.search([
            ('country_code', '=', country_code),
            ('active', '=', True)
        ], limit=1)
        
        if config:
            return config.redirect_url
        
        return None
    
    @http.route(['/'], type='http', auth='public', website=True)
    def website_redirect(self, **kwargs):
        """Intercept homepage requests and redirect based on geolocation"""
        
        _logger.info('=== GEO REDIRECT: Route triggered ===')
        
        # Check if user has opted out of auto-redirect (via query parameter)
        if kwargs.get('no_redirect'):
            _logger.info('User opted out of redirect via no_redirect parameter')
            return request.redirect('/shop')
        
        # Get current host first
        current_host = request.httprequest.host
        _logger.info(f'Current host: {current_host}')
        
        # Get client IP
        ip_address = self._get_client_ip()
        _logger.info(f'Client IP: {ip_address}')
        
        # Get country from IP
        country_code = self._get_country_from_ip(ip_address)
        _logger.info(f'Detected country code: {country_code}')
        
        # Get redirect URL for country
        redirect_url = self._get_redirect_url(country_code)
        _logger.info(f'Redirect URL: {redirect_url}')
        
        if redirect_url:
            # Extract the target host from redirect URL
            from urllib.parse import urlparse
            target_host = urlparse(redirect_url).netloc
            _logger.info(f'Target host: {target_host}, Current host: {current_host}')
            
            # Only redirect if we're NOT already on the correct target domain
            if target_host != current_host:
                # Add /shop to the redirect URL to land directly on the shop page
                full_redirect_url = redirect_url.rstrip('/') + '/shop'
                _logger.info(f'REDIRECTING from {current_host} to {full_redirect_url}')
                
                # Use JavaScript redirect for more reliable cross-domain redirect
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
                        <p>If you are not redirected automatically, <a href="{full_redirect_url}">click here</a>.</p>
                    </body>
                    </html>
                ''')
            else:
                _logger.info(f'Already on correct target domain ({target_host}), continuing to shop')
        else:
            _logger.info('No redirect URL found for this country, staying on current domain')
        
        # Continue to normal homepage/shop
        _logger.info('Continuing to /shop')
        return request.redirect('/shop')

    @http.route(['/geo/test'], type='http', auth='public')
    def test_geo(self, **kwargs):
        """Test geolocation detection"""
        ip = self._get_client_ip()
        country = self._get_country_from_ip(ip)
        redirect_url = self._get_redirect_url(country)
        
        return f"""
        <h1>Geo Test</h1>
        <p>IP: {ip}</p>
        <p>Country: {country}</p>
        <p>Redirect URL: {redirect_url}</p>
        <p>Session redirected: {request.session.get('geo_redirected')}</p>
        <p>Current host: {request.httprequest.host}</p>
        """