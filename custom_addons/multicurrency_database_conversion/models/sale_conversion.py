from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    actual_foreign_amount = fields.Monetary(
        string='Foreign Currency Amount',
        currency_field='currency_id',
        compute='_compute_actual_foreign_amount',
        store=True
    )

    amount_in_myr = fields.Monetary(
        string='Amount in MYR',
        currency_field='myr_currency_id',
        compute='_compute_amount_in_myr',
        store=True
    )

    myr_currency_id = fields.Many2one(
        'res.currency',
        string='MYR Currency',
        compute='_compute_myr_currency_id',
        store=True
    )

    @api.depends('amount_total')
    def _compute_actual_foreign_amount(self):
        for order in self:
            order.actual_foreign_amount = order.amount_total

    @api.depends('amount_total', 'currency_id', 'company_id', 'date_order')
    def _compute_amount_in_myr(self):
        myr_currency = self._get_myr_currency()
        for order in self:
            if order.currency_id and myr_currency:
                order.amount_in_myr = order.currency_id._convert(
                    order.amount_total,
                    myr_currency,
                    order.company_id,
                    order.date_order or fields.Date.today()
                )
            else:
                order.amount_in_myr = 0.0

    @api.depends('company_id')
    def _compute_myr_currency_id(self):
        myr_currency = self._get_myr_currency()
        for order in self:
            order.myr_currency_id = myr_currency

    @api.model
    def _get_myr_currency(self):
        """Returns the MYR currency record safely."""
        currency = self.env['res.currency'].search([('name', '=', 'MYR')], limit=1)
        if not currency:
            raise UserError("MYR currency not found in the system. Please configure MYR in Accounting > Currencies.")
        return currency
