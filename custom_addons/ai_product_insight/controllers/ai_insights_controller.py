# controllers/ai_insights_controller.py
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class AIInsightsController(http.Controller):
    
    @http.route('/ai_insights/generate', type='json', auth='public', methods=['POST'])
    def generate_insights(self, product_id):
        """Generate AI insights for a product"""
        try:
            _logger.info(f"Generate insights called with product_id: {product_id}")
            
            # Ensure product_id is an integer
            product_id = int(product_id)
            
            # Use sudo() to bypass permission checks for AI insights generation
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                _logger.error(f"Product not found for ID: {product_id}")
                return {'success': False, 'error': 'Product not found'}
            
            _logger.info(f"Found product: {product.name}")
            
            # Generate insights with sudo privileges
            product.generate_ai_insights()
            
            # Return formatted insights - call on the product instance
            insights = product.get_ai_insights_formatted()
            
            # If insights is None, return a proper response
            if insights is None:
                _logger.error("Failed to generate insights - insights returned None")
                return {'success': False, 'error': 'Failed to generate insights'}
            
            _logger.info(f"Successfully generated insights: {insights}")
            return insights
            
        except ValueError as e:
            _logger.error(f"Invalid product_id format: {product_id} - {str(e)}")
            return {'success': False, 'error': 'Invalid product ID format'}
        except Exception as e:
            _logger.error(f"Error in generate_insights: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    @http.route('/ai_insights/get', type='json', auth='public', methods=['POST'])
    def get_insights(self, product_id):
        """Get existing AI insights for a product"""
        try:
            _logger.info(f"Get insights called with product_id: {product_id}")
            
            # Ensure product_id is an integer
            product_id = int(product_id)
            
            # Use sudo() to bypass permission checks for reading insights
            product = request.env['product.template'].sudo().browse(product_id)
            if not product.exists():
                _logger.error(f"Product not found for ID: {product_id}")
                return {'success': False, 'error': 'Product not found'}
            
            _logger.info(f"Found product: {product.name}")
            
            # Call the method on the product instance, not as a model method
            insights = product.get_ai_insights_formatted()
            
            # If insights is None or empty, return a proper response
            if insights is None:
                _logger.info("No existing insights found")
                return {'success': True, 'data': None}
            
            _logger.info(f"Retrieved insights: {insights}")
            return insights
            
        except ValueError as e:
            _logger.error(f"Invalid product_id format: {product_id} - {str(e)}")
            return {'success': False, 'error': 'Invalid product ID format'}
        except Exception as e:
            _logger.error(f"Error in get_insights: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    @http.route('/ai_insights/modal', type='http', auth='user', methods=['GET'])
    def insights_modal(self, product_id):
        """Render the AI insights modal"""
        try:
            product_id = int(product_id)
            product = request.env['product.template'].browse(product_id)
            if not product.exists():
                return request.render('ai_product_insights.error_modal', {'error': 'Product not found'})
            
            # Get insights - fix method call (remove product_id parameter)
            insights_data = product.get_ai_insights_formatted()
            
            return request.render('ai_product_insights.insights_modal', {
                'product': product,
                'insights': insights_data
            })
            
        except ValueError as e:
            _logger.error(f"Invalid product_id format: {product_id} - {str(e)}")
            return request.render('ai_product_insights.error_modal', {'error': 'Invalid product ID format'})
        except Exception as e:
            _logger.error(f"Error in insights_modal: {str(e)}", exc_info=True)
            return request.render('ai_product_insights.error_modal', {'error': str(e)})