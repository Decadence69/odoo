# models/promotion_setup.py
from odoo import models, fields

class PromotionSetup(models.Model):
    _name = 'promotion.setup'
    _description = 'Promotion Setup'

    name = fields.Char(string='Promotion Name', required=True)
    website_id = fields.Many2one('website', string='Website', required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date', required=True)
    active = fields.Boolean(string='Active', default=True)
    
    # Use Text field to store raw HTML without escaping
    html_content = fields.Text(
        string='Banner HTML Content', 
        help='Write your custom HTML for the banner. Use inline styles for best results.'
    )
    background_image = fields.Binary(
        string='Background Image', 
        attachment=True,
        help='Upload a background image for the banner'
    )
    bg_color = fields.Char(
        string='Background Color', 
        help='Fallback background color if no image (e.g., #0000ff or blue)',
        default='#f8f9fa'
    )
    
    # Legacy fields
    text_to_display = fields.Text(string='Text to Display')
    text_color = fields.Char(string='Text Color')
    btn_color = fields.Char(string='Button Color')
    btn_txt_color = fields.Char(string='Button Text Color')
    url = fields.Char(string='URL')