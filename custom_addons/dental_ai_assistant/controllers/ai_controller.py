from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class DentalAIController(http.Controller):
    
    @http.route('/api/dental-ai/recommend', type='json', auth='user', methods=['POST'], csrf=False)
    def get_recommendation(self, **kwargs):
        """API endpoint for getting bur recommendations"""
        try:
            query = kwargs.get('query', '')
            
            if not query:
                return {
                    'success': False,
                    'error': 'Query is required'
                }
            
            ai_assistant = request.env['dental.ai.assistant']
            result = ai_assistant.get_bur_recommendation(query)
            
            return result
            
        except Exception as e:
            _logger.error(f"API error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @http.route('/api/dental-ai/history', type='json', auth='user', methods=['GET'])
    def get_recommendation_history(self, **kwargs):
        """Get user's recommendation history"""
        try:
            limit = kwargs.get('limit', 10)
            user_id = request.env.user.id
            
            records = request.env['dental.ai.assistant'].search([
                ('created_by', '=', user_id)
            ], limit=limit, order='date_created desc')
            
            history = []
            for record in records:
                history.append({
                    'id': record.id,
                    'query': record.query,
                    'recommendation': record.recommendation,
                    'sources': record.sources,
                    'confidence_score': record.confidence_score,
                    'date_created': record.date_created.isoformat() if record.date_created else None
                })
            
            return {
                'success': True,
                'history': history
            }
            
        except Exception as e:
            _logger.error(f"History API error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }