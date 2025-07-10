from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PaymentAcquirer(models.Model):
    _name = 'payment.acquirer'
    _description = 'Payment Acquirer'
    _order = 'sequence, name'
    _check_company_auto = True

    name = fields.Char(string='Name', required=True, translate=True)
    provider_id = fields.Many2one('payment.provider', string='Provider', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    website_published = fields.Boolean('Available in Website', default=False)
    state = fields.Selection([
        ('disabled', 'Disabled'),
        ('enabled', 'Enabled'),
        ('test', 'Test Mode'),
    ], string='State', default='disabled', required=True)

    sequence = fields.Integer(default=10)

    # Other optional fields for full behavior:
    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', company_id)]",
        required=False,
        help='The journal where payments made using this acquirer will be recorded.'
    )

    payment_method_line_ids = fields.One2many(
        'account.payment.method.line',
        'acquirer_id',
        string='Payment Methods',
        readonly=True,
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'The name of the payment acquirer must be unique per company!')
    ]
