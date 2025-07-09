from odoo import models, fields, api
import requests

class SaltEdgeSettings(models.Model):
    _name = 'salt.edge.settings'
    _description = 'Salt Edge API Settings'

    name = fields.Char(default="Configuration")
    app_id = fields.Char(required=True)
    secret = fields.Char(required=True)

    def connect_to_salt_edge(self):
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'App-id': self.app_id,
            'Secret': self.secret
        }
        response = requests.get('https://www.saltedge.com/api/v5/customers', headers=headers)
        return response.json()

class SaltEdgeBankAccount(models.Model):
    _name = 'salt.edge.account'
    _description = 'Salt Edge Bank Account'

    name = fields.Char()
    account_id = fields.Char()
    balance = fields.Float()
    currency = fields.Char()
    connection_id = fields.Char()

class SaltEdgeTransaction(models.Model):
    _name = 'salt.edge.transaction'
    _description = 'Salt Edge Transaction'

    account_id = fields.Many2one('salt.edge.account')
    made_on = fields.Date()
    description = fields.Char()
    amount = fields.Float()
    currency = fields.Char()