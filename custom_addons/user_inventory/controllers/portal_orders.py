from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.sale.controllers.portal import CustomerPortal as SalePortal

class CustomSalePortal(SalePortal):

    @http.route(['/my/orders'], type='http', auth="user", website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        # Use the default logic first
        response = super().portal_my_orders(page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, **kw)

        # Rebuild the order list with additional states
        orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', request.env.user.partner_id.id),
            ('state', 'in', ['draft', 'sent', 'sale', 'done', 'cancel'])  # Include Placed orders
        ], order='date_order desc')

        response.qcontext['orders'] = orders
        return request.render("sale.portal_my_orders", response.qcontext)
