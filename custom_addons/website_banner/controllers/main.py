# controllers/main.py
from odoo import http
from odoo.http import request
from datetime import datetime
from markupsafe import Markup
import json

class WebsiteBanner(http.Controller):
    @http.route('/home/banner', type='http', auth="public", website=True, csrf=False)
    def index(self, **kw):
        promos = request.env['promotion.setup'].sudo().search([
            ('website_id', '=', request.website.id),
            ('active', '=', True)
        ])
        html = ''
        bg_image = ''
        bg_color = ''
        
        now = datetime.now()

        for promo in promos:
            if promo.start_date <= now <= promo.end_date:
                # Get the raw HTML content without sanitization
                html = str(promo.html_content) if promo.html_content else ''
                
                # Get background image as base64
                if promo.background_image:
                    bg_image = promo.background_image.decode('utf-8') if isinstance(promo.background_image, bytes) else str(promo.background_image)
                
                bg_color = promo.bg_color or ''
                break  # Only show first active promo
        
        # Set proper content type header
        response = request.make_response(
            json.dumps({
                'html': html,
                'bg_image': bg_image,
                'bg_color': bg_color
            }),
            headers=[
                ('Content-Type', 'application/json'),
                ('Cache-Control', 'no-cache')
            ]
        )
        return response