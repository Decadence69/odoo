from odoo import models, fields

class UserInventoryLine(models.Model):
    _name = 'user.inventory.line'
    _description = 'User Inventory Line'
    _order = 'sequence'

    user_id = fields.Many2one('res.users', string="User", required=True)
    product_id = fields.Many2one('product.product', string="Product")
    custom_name = fields.Char(string="Custom Item Name")
    is_custom = fields.Boolean(string="Custom Entry", default=False)
    current_qty = fields.Integer(string="Current Stock", default=0)
    total_ordered_qty = fields.Integer(string="Total Ordered", default=0)
    target_qty = fields.Integer(string="Target Stock", default=0)
    sequence = fields.Integer(string="Sequence", default=10)
    
    _sql_constraints = [
        ('user_product_unique', 'unique(user_id, product_id)', 'Each user can only track one entry per product.')
    ]
