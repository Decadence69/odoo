from odoo import models, fields, api

class AIInsights(models.Model):
    _name = 'ai.insights'
    _description = 'AI Insights History'
    
    product_id = fields.Many2one('product.template', string='Product', required=True)
    insights = fields.Text(string='Insights', required=True)
    generated_date = fields.Datetime(string='Generated Date', default=fields.Datetime.now)
    token_usage = fields.Integer(string='Token Usage')