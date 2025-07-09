from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)


class SaltEdgeSettings(models.Model):
    _name = 'salt.edge.settings'
    _description = 'Salt Edge API Settings'

    name = fields.Char(default="Configuration")
    app_id = fields.Char(required=True)
    secret = fields.Char(required=True)

    @api.model
    def get_credentials(self):
        """Returns the first saved Salt Edge credentials."""
        config = self.search([], limit=1)
        if not config:
            raise ValueError("Salt Edge configuration not found.")
        return config.app_id, config.secret


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


class SaltEdgeAPI(models.Model):
    _name = 'salt.edge.api'
    _description = 'Salt Edge API Integration'

    def _get_auth_headers(self):
        app_id, secret = self.env['salt.edge.settings'].get_credentials()
        return {
            'App-id': app_id,
            'Secret': secret,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def call_api(self, endpoint, method='GET', payload=None):
        """Generic method to call Salt Edge API."""
        headers = self._get_auth_headers()
        url = f'https://www.saltedge.com{endpoint}'
        try:
            if method == 'GET':
                res = requests.get(url, headers=headers)
            elif method == 'POST':
                res = requests.post(url, json=payload, headers=headers)
            else:
                raise ValueError("Unsupported method")
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException as e:
            _logger.exception("Salt Edge API error")
            return {'error': str(e)}

    def sync_customers(self):
        """Example: Fetch list of customers."""
        return self.call_api('/api/v5/customers')

    def sync_accounts(self):
        """Fetch and store bank accounts from Salt Edge."""
        response = self.call_api('/api/v5/accounts')
        if 'data' in response:
            for acc in response['data']:
                self.env['salt.edge.account'].create({
                    'name': acc.get('name'),
                    'account_id': acc.get('id'),
                    'balance': acc.get('balance', {}).get('amount'),
                    'currency': acc.get('balance', {}).get('currency_code'),
                    'connection_id': acc.get('connection_id'),
                })
        return response

    def sync_transactions(self, account_id):
        """Fetch and store transactions for a specific account."""
        response = self.call_api(f'/api/v5/transactions?account_id={account_id}')
        if 'data' in response:
            account = self.env['salt.edge.account'].search([('account_id', '=', account_id)], limit=1)
            for tx in response['data']:
                self.env['salt.edge.transaction'].create({
                    'account_id': account.id if account else None,
                    'made_on': tx.get('made_on'),
                    'description': tx.get('description'),
                    'amount': tx.get('amount'),
                    'currency': tx.get('currency_code'),
                })
        return response
