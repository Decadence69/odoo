from odoo import models, api
import requests

class SaltEdgeSyncWizard(models.TransientModel):
    _name = 'salt.edge.sync.wizard'
    _description = 'Salt Edge Sync Wizard'

    @api.model
    def sync_accounts(self):
        config = self.env['salt.edge.settings'].search([], limit=1)
        if not config:
            raise Exception("Salt Edge configuration not found.")

        headers = {
            'App-id': config.app_id,
            'Secret': config.secret,
            'Accept': 'application/json'
        }

        url = 'https://www.saltedge.com/api/v5/accounts'
        response = requests.get(url, headers=headers)
        data = response.json()

        for acc in data.get('data', []):
            self.env['salt.edge.account'].create({
                'name': acc.get('name'),
                'account_id': acc.get('id'),
                'balance': acc.get('balance').get('amount'),
                'currency': acc.get('currency'),
                'connection_id': acc.get('connection_id'),
            })
