import requests
from odoo import models, fields, api

class SaltEdgeDemo(models.Model):
    _name = 'salt.edge.demo'
    _description = 'Salt Edge Sandbox Demo'

    name = fields.Char(string='Demo Provider Name', default='Fake Bank')

    def action_connect_sandbox(self):
        """Simulate a connection via Salt Edge sandbox"""
        headers = {
            'App-id': 'UiZswfh8Ww45bfqtv9s-SMePwoYUQ-cCwjWM6yqwDWg',
            'Secret': 'jIqtUkw1W5pZp21FC1j7hLN3dCSrM0BPETuviEuhUew',
            'Content-Type': 'application/json'
        }

        data = {
            "data": {
                "customer_id": "demo-customer-001",
                "provider_code": "fakebank_simple_xf",
                "consent": {
                    "scopes": ["account_details", "transactions_details"]
                },
                "attempt": {
                    "return_to": "https://example.com/return"
                }
            }
        }

        response = requests.post("https://www.saltedge.com/api/v5/attempts", headers=headers, json=data)

        if response.status_code == 200:
            return response.json()['data']['redirect_url']
        else:
            raise Exception(f"Salt Edge Sandbox error: {response.text}")
