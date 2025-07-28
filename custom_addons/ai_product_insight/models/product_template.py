# models/product_template.py
from odoo import models, fields, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    ai_insights = fields.Text(string='AI Insights', help='AI-generated insights about this product')
    ai_insights_last_updated = fields.Datetime(string='AI Insights Last Updated')
    
    def generate_ai_insights(self):
        """Generate AI insights for dental bur products using Google Gemini"""
        for product in self:
            try:
                # Get your Gemini API key from system parameters
                gemini_api_key = self.env['ir.config_parameter'].sudo().get_param('ai_product_insights.gemini_api_key')
                
                if not gemini_api_key:
                    raise ValueError("Gemini API key not configured. Please set 'ai_product_insights.gemini_api_key' in system parameters.")
                
                # Prepare product data for AI analysis - handle missing fields gracefully
                product_data = {
                    'name': product.name or '',
                    'description': product.description_sale or product.description or '',
                    'category': product.categ_id.name if product.categ_id else '',
                    'price': product.list_price or 0.0,
                    'attributes': [attr.name for attr in product.attribute_line_ids.mapped('attribute_id')] if hasattr(product, 'attribute_line_ids') else [],
                }
                
                # Handle tags - check for different possible field names
                tags = []
                if hasattr(product, 'tag_ids'):
                    tags = [tag.name for tag in product.tag_ids] if product.tag_ids else []
                elif hasattr(product, 'product_tag_ids'):
                    tags = [tag.name for tag in product.product_tag_ids] if product.product_tag_ids else []
                elif hasattr(product, 'tags'):
                    tags = [tag.name for tag in product.tags] if product.tags else []
                
                product_data['tags'] = tags
                
                # Add default currency if available
                currency = self.env.company.currency_id.symbol if self.env.company.currency_id else '$'
                
                # Create dental-specific prompt for Gemini
                prompt = f"""
                You are a dental specialist analyzing dental burs for professional dentists. Analyze this dental bur product and provide clinical insights in JSON format:
                
                Product: {product_data['name']}
                Description: {product_data['description']}
                Category: {product_data['category']}
                Price: {currency}{product_data['price']}
                Attributes: {', '.join(product_data['attributes']) if product_data['attributes'] else 'None specified'}
                Tags: {', '.join(product_data['tags']) if product_data['tags'] else 'None specified'}
                
                Please provide professional dental insights in the following JSON structure. Make sure to return valid JSON only, no additional text:
                {{
                    "clinical_features": ["specific feature relevant to dental work", "cutting efficiency detail", "durability aspect"],
                    "recommended_procedures": ["specific dental procedure 1", "specific dental procedure 2", "specific dental procedure 3"],
                    "material_specifications": ["material composition", "coating information", "hardness rating"],
                    "performance_characteristics": ["cutting speed", "precision level", "vibration reduction"],
                    "compatibility_notes": ["handpiece compatibility", "speed recommendations", "irrigation requirements"],
                    "clinical_advantages": ["advantage in clinical setting", "patient comfort benefit", "time efficiency gain"]
                }}
                
                Focus on:
                - Specific dental procedures this bur is designed for
                - Clinical performance characteristics that matter to dentists
                - Technical specifications relevant to dental practice
                - Practical advantages in clinical settings
                - Patient comfort and safety considerations
                
                Avoid generic marketing language. Use professional dental terminology that practicing dentists would understand and find useful.
                """
                
                # Call Gemini API
                insights = self._call_gemini_api(gemini_api_key, prompt)
                
                # Validate and clean the response
                cleaned_insights = self._validate_and_clean_json(insights)
                
                # Update product with insights
                product.write({
                    'ai_insights': cleaned_insights,
                    'ai_insights_last_updated': fields.Datetime.now(),
                })
                
                _logger.info(f"Generated AI insights for dental bur: {product.name}")
                
            except Exception as e:
                _logger.error(f"Error generating AI insights for product {product.name}: {str(e)}")
                raise
    
    def _validate_and_clean_json(self, raw_response):
        """Validate and clean JSON response from AI"""
        try:
            # Try to find JSON within the response
            cleaned = raw_response.strip()
            
            # Remove common markdown formatting if present
            if cleaned.startswith('```json'):
                cleaned = cleaned[7:]
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3]
            
            cleaned = cleaned.strip()
            
            # Try to parse as JSON
            json.loads(cleaned)  # This will raise an exception if invalid
            return cleaned
            
        except json.JSONDecodeError:
            _logger.warning(f"Received invalid JSON from AI: {raw_response}")
            # Return a fallback JSON structure with the raw text
            fallback = {
                "raw_text": raw_response,
                "key_features": [],
                "target_audience": "General consumers",
                "use_cases": [],
                "competitive_advantages": [],
                "recommendations": [],
                "marketing_angles": []
            }
            return json.dumps(fallback)
    
    def _call_gemini_api(self, api_key, prompt):
        """Call Google Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}"
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    return content
                else:
                    raise ValueError("No content generated by Gemini")
            else:
                error_msg = f"Gemini API error: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise ValueError(error_msg)
                
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Network error calling Gemini API: {str(e)}")
    
    def get_ai_insights_formatted(self):
        """Get formatted AI insights for display"""
        if not self.ai_insights:
            return None
            
        try:
            # Try to parse as JSON first
            insights_data = json.loads(self.ai_insights)
            return {
                'success': True,
                'data': insights_data,
                'last_updated': self.ai_insights_last_updated.strftime('%Y-%m-%d %H:%M:%S') if self.ai_insights_last_updated else None
            }
        except json.JSONDecodeError:
            # If not JSON, return as plain text
            return {
                'success': True,
                'data': {'raw_text': self.ai_insights},
                'last_updated': self.ai_insights_last_updated.strftime('%Y-%m-%d %H:%M:%S') if self.ai_insights_last_updated else None
            }
        except Exception as e:
            _logger.error(f"Error formatting insights for product {self.name}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }