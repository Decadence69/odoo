from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.ecommerce_geo_redirect.controllers.main import GeoRedirectService  # Import the service
import logging

_logger = logging.getLogger(__name__)


class CategoryGridController(http.Controller):
    
    @http.route('/', type='http', auth='public', website=True, sitemap=True)
    def category_grid(self, **kwargs):
        """Display all product categories in a grid layout"""
        
        # Check for geo redirect FIRST
        redirect = GeoRedirectService.check_redirect(**kwargs)
        if redirect:
            return redirect
        
        # If no redirect needed, continue with normal logic
        current_website = request.website
        
        categories = request.env['product.public.category'].search([
            '|',
            ('website_id', '=', False),
            ('website_id', '=', current_website.id),
            ('parent_id', '=', False)
        ], order='sequence, name')
        
        category_data = []
        for category in categories:
            slug = request.env['ir.http']._slug(category)
            category_data.append({
                'category': category,
                'url': f'/shop/category/{slug}',
            })
        
        values = {
            'category_data': category_data,
            'website': current_website,
        }
        
        return request.render('category_grid.category_grid_page', values)