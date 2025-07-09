from odoo import models, api
import requests

class SaltEdgeAPI(models.Model):
    _name = 'salt.edge.api'
    _description = 'Salt Edge API Handler'

    @api.model
    def connect_to_salt_edge(self):
        app_id = self.env['ir.config_parameter'].sudo().get_param('salt_edge_integration.app_id')
        secret = self.env['ir.config_parameter'].sudo().get_param('salt_edge_integration.secret')

        if not app_id or not secret:
            raise ValueError("Salt Edge credentials are missing. Please configure them in the settings.")

        headers = {
            'App-id': app_id,
            'Secret': secret,
            'Content-Type': 'application/json'
        }

        # Sample call to Salt Edge API (adjust URL and data as needed)
        response = requests.get('https://www.saltedge.com/api/v5/customers', headers=headers)

        if response.status_code != 200:
            raise Exception(f"Salt Edge API error: {response.text}")

        return response.json()
