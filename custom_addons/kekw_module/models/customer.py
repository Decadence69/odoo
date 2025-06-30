from odoo import api, fields, models


class CustomerInventory(models.Model):
    _name = 'customer.name'
    _description = 'Customer'

    name = fields.Char(string="Name", required=True)
    product_ID = fields.Char(string="ProductIDs")
    phone = fields.Char(string="Phone Number")
    address = fields.Text(string="Address")
    testfield = fields.Text(string="Test Field")    
    newfield = fields.Text(string="Test Field 2")    
    newfield_again = fields.Text(string="Test Field 3")    

