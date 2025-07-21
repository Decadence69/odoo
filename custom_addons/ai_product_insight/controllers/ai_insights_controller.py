# controllers/ai_insights_controller.py
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class AIInsightsController(http.Controller):
    
    @http.route('/ai_insights/generate', type='json', auth='user', methods=['POST'])
    def generate_insights(self, product_id):
        """Generate AI insights for a product"""
        try:
            product = request.env['product.template'].browse(int(product_id))
            if not product.exists():
                return {'success': False, 'error': 'Product not found'}
            
            # Generate insights
            product.generate_ai_insights()
            
            # Return formatted insights - call on the product instance
            insights = product.get_ai_insights_formatted()
            
            # If insights is None, return a proper response
            if insights is None:
                return {'success': False, 'error': 'Failed to generate insights'}
            
            return insights
            
        except Exception as e:
            _logger.error(f"Error in generate_insights: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/ai_insights/get', type='json', auth='user', methods=['POST'])
    def get_insights(self, product_id):
        """Get existing AI insights for a product"""
        try:
            product = request.env['product.template'].browse(int(product_id))
            if not product.exists():
                return {'success': False, 'error': 'Product not found'}
            
            # Call the method on the product instance, not as a model method
            insights = product.get_ai_insights_formatted()
            
            # If insights is None or empty, return a proper response
            if insights is None:
                return {'success': True, 'data': None}
            
            return insights
            
        except Exception as e:
            _logger.error(f"Error in get_insights: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @http.route('/ai_insights/modal', type='http', auth='user', methods=['GET'])
    def insights_modal(self, product_id):
        """Render the AI insights modal"""
        try:
            product = request.env['product.template'].browse(int(product_id))
            if not product.exists():
                return request.render('ai_product_insights.error_modal', {'error': 'Product not found'})
            
            # Get insights
            insights_data = product.get_ai_insights_formatted(product_id)
            
            return request.render('ai_product_insights.insights_modal', {
                'product': product,
                'insights': insights_data
            })
            
        except Exception as e:
            _logger.error(f"Error in insights_modal: {str(e)}")
            return request.render('ai_product_insights.error_modal', {'error': str(e)})