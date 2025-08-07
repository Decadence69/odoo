from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import json
import os
from .dental_rag_system import DentalRAGSystem

_logger = logging.getLogger(__name__)

class DentalAIAssistant(models.Model):
    _name = 'dental.ai.assistant'
    _description = 'Dental AI Assistant for Bur Recommendations'
    _rec_name = 'query'
    
    query = fields.Text(string='Dentist Query', required=True)
    recommendation = fields.Html(string='AI Recommendation')
    sources = fields.Text(string='Knowledge Sources')
    confidence_score = fields.Float(string='Confidence Score')
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    date_created = fields.Datetime(string='Date Created', default=fields.Datetime.now)
    
    def _get_rag_system(self):
        """Initialize and return RAG system with configuration"""
        # Get API key from system parameters
        api_key = self.env['ir.config_parameter'].sudo().get_param('dental_ai.gemini_api_key')
        if not api_key:
            raise UserError(_("Gemini API key not configured. Please configure it in System Parameters."))

        # Get knowledge base path
        knowledge_base_path = self.env['ir.config_parameter'].sudo().get_param(
            'dental_ai.knowledge_base_path',
            '/tmp/dental_knowledge_db'
        )
        
        # Ensure directory exists
        os.makedirs(knowledge_base_path, exist_ok=True)

        try:
            rag_system = DentalRAGSystem(api_key, knowledge_base_path)
            # Try to load existing knowledge base
            if not rag_system.load_existing_knowledge_base():
                _logger.warning("No existing knowledge base found. Please build the knowledge base first.")
            return rag_system
        except Exception as e:
            _logger.error(f"Failed to initialize RAG system: {str(e)}")
            raise UserError(_("Failed to initialize AI system: %s") % str(e))
    
    def get_ai_recommendation(self):
        """Get AI recommendation for the current record's query"""
        self.ensure_one()
        
        if not self.query:
            raise UserError(_("Please enter a query first."))
        
        try:
            rag_system = self._get_rag_system()
            result = rag_system.get_recommendation(self.query)
            
            if result['success']:
                # Update the current record with the recommendation
                self.write({
                    'recommendation': result['recommendation'],
                    'sources': ', '.join(result.get('sources', [])),
                    'confidence_score': min(result.get('confidence_scores', [1.0])) if result.get('confidence_scores') else 1.0
                })
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('AI recommendation generated successfully'),
                        'type': 'success',
                    }
                }
            else:
                raise UserError(_("Failed to get recommendation: %s") % result.get('error', 'Unknown error'))
                
        except Exception as e:
            _logger.error(f"Error getting AI recommendation: {str(e)}")
            raise UserError(_("Failed to get AI recommendation: %s") % str(e))
    
    @api.model
    def get_bur_recommendation(self, query):
        """Get AI recommendation for dental procedure"""
        try:
            rag_system = self._get_rag_system()
            result = rag_system.get_recommendation(query)
            
            if result['success']:
                # Create record for tracking
                record = self.create({
                    'query': query,
                    'recommendation': result['recommendation'],
                    'sources': ', '.join(result.get('sources', [])),
                    'confidence_score': min(result.get('confidence_scores', [1.0])) if result.get('confidence_scores') else 1.0
                })
                
                return {
                    'success': True,
                    'recommendation': result['recommendation'],
                    'sources': result.get('sources', []),
                    'record_id': record.id
                }
            else:
                return result
                
        except Exception as e:
            _logger.error(f"Error getting recommendation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @api.model
    def build_knowledge_base(self, jsonl_file_path):
        """Build knowledge base from JSONL file"""
        try:
            rag_system = self._get_rag_system()
            
            if not os.path.exists(jsonl_file_path):
                raise UserError(_("JSONL file not found: %s") % jsonl_file_path)
            
            result = rag_system.build_knowledge_base(jsonl_file_path)
            
            if result:
                return {
                    'success': True,
                    'message': 'Knowledge base built successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to build knowledge base'
                }
                
        except Exception as e:
            _logger.error(f"Error building knowledge base: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def action_regenerate_recommendation(self):
        """Regenerate recommendation for existing query"""
        self.ensure_one()
        result = self.get_bur_recommendation(self.query)
        
        if result['success']:
            self.write({
                'recommendation': result['recommendation'],
                'sources': ', '.join(result.get('sources', [])),
                'confidence_score': min(result.get('confidence_scores', [1.0])) if result.get('confidence_scores') else 1.0
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Recommendation regenerated successfully'),
                    'type': 'success',
                }
            }
        else:
            raise UserError(_("Failed to regenerate recommendation: %s") % result.get('error', 'Unknown error'))

class DentalAIConfiguration(models.TransientModel):
    _name = 'dental.ai.config'
    _description = 'Dental AI Configuration'
    _inherit = 'res.config.settings'
    
    gemini_api_key = fields.Char(string='Gemini API Key')
    knowledge_base_path = fields.Char(string='Knowledge Base Path', default='/tmp/dental_knowledge_db')
    jsonl_file_path = fields.Char(string='JSONL Blog File Path')
    
    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update({
            'gemini_api_key': params.get_param('dental_ai.gemini_api_key', ''),
            'knowledge_base_path': params.get_param('dental_ai.knowledge_base_path', '/tmp/dental_knowledge_db'),
            'jsonl_file_path': params.get_param('dental_ai.jsonl_file_path', ''),
        })
        return res
    
    def set_values(self):
        super().set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('dental_ai.gemini_api_key', self.gemini_api_key or '')
        params.set_param('dental_ai.knowledge_base_path', self.knowledge_base_path or '/tmp/dental_knowledge_db')
        params.set_param('dental_ai.jsonl_file_path', self.jsonl_file_path or '')
    
    def action_build_knowledge_base(self):
        """Build knowledge base from configured JSONL file"""
        if not self.jsonl_file_path:
            raise UserError(_("Please configure the JSONL file path first"))
        
        ai_assistant = self.env['dental.ai.assistant']
        result = ai_assistant.build_knowledge_base(self.jsonl_file_path)
        
        if result['success']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': result['message'],
                    'type': 'success',
                }
            }
        else:
            raise UserError(_("Failed to build knowledge base: %s") % result['error'])
    
    def action_test_connection(self):
        """Test Gemini API connection"""
        if not self.gemini_api_key:
            raise UserError(_("Please enter Gemini API key first"))
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            
            # Try different model names that are currently available
            model_names = [
                'gemini-1.5-flash',
                'gemini-1.5-pro', 
                'gemini-1.0-pro',
                'models/gemini-1.5-flash',
                'models/gemini-1.5-pro'
            ]
            
            success = False
            working_model = None
            
            for model_name in model_names:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content("Hello, this is a test.")
                    working_model = model_name
                    success = True
                    break
                except Exception as model_error:
                    _logger.info(f"Model {model_name} failed: {str(model_error)}")
                    continue
            
            if success:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Success'),
                        'message': _('Gemini API connection successful with model: %s') % working_model,
                        'type': 'success',
                    }
                }
            else:
                # List available models for debugging
                try:
                    available_models = genai.list_models()
                    model_list = [model.name for model in available_models if 'generateContent' in model.supported_generation_methods]
                    raise UserError(_("No working model found. Available models: %s") % ', '.join(model_list[:5]))
                except Exception as list_error:
                    raise UserError(_("API connection failed. Please check your API key and try again."))
                    
        except Exception as e:
            raise UserError(_("API connection failed: %s") % str(e))