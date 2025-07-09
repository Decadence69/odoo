from odoo import models, fields

class SaltEdgeSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    app_id = fields.Char(
        string="App ID",
        config_parameter='salt_edge_integration.app_id'
    )
    secret = fields.Char(
        string="Secret Key",
        config_parameter='salt_edge_integration.secret'
    )
