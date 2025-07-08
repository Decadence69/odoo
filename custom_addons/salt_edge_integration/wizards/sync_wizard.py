from odoo import models, fields, api
import requests
import uuid

class SaltEdgeSyncWizard(models.TransientModel): #just a temporary form
    _name = 'salt.edge.sync.wizard'
    _description = 'Salt Edge Sync Wizard'

    country_code = fields.Char(default='GB')
    provider_code = fields.Char(required=True, help="fakebank_simple_xf") #salt edge code for bank eg: fakebank_simple_xf

    def _get_headers(self):
        config = self.env['salt.edge.settings'].search([], limit=1)
        return {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'App-id': config.app_id,
            'Secret': config.secret,
            'Expires-at': '0',
            'Client-User-Id': str(uuid.uuid4())
        }

    def create_customer(self):
        url = 'https://www.saltedge.com/api/v5/customers'
        payload = {'data': {'identifier': str(uuid.uuid4())}}
        res = requests.post(url, json=payload, headers=self._get_headers())
        return res.json()['data']['id']

    def create_connect_session(self, provider_code):
        customer_id = self.create_customer()
        payload = {
            "data": {
                "customer_id": customer_id,
                "consent": {
                    "scopes": ["account_details", "transactions_details"]
                },
                "attempt": {
                    "fetch_scopes": ["account_details", "transactions_details"]
                },
                "provider_code": provider_code,
                "return_to": "http://192.168.0.188:8069/saltedge/callback"
            }
        }
        url = 'https://www.saltedge.com/api/v5/connect_sessions/create'

        res = requests.post(url, json=payload, headers=self._get_headers())
        return res.json()['data']['connect_url']

    def action_sync(self):
        link = self.create_connect_session(self.provider_code)
        return {
            'type': 'ir.actions.act_url',
            'url': link,
            'target': 'new',
        }
    config = self.env['salt.edge.settings'].search([], limit=1)

headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'App-id': config.app_id,
    'Secret': config.secret,
    'Expires-at': '0',
    'Client-User-Id': str(uuid.uuid4())
}
