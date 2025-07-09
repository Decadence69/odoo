from odoo import models

from odoo.addons.payment.models.payment_provider import ProviderSelection

# Add Salt Edge to the provider selection list
ProviderSelection.add('salt_edge', "Salt Edge")
