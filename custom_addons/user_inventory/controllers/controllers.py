from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class PortalInventory(http.Controller):

    @http.route(['/my/inventory'], type='http', auth='user', website=True)
    def portal_inventory(self, **kw):
        user = request.env.user
        inventory_model = request.env['user.inventory.line'].sudo()

        # Fetch all confirmed orders
        orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', user.partner_id.id),
            ('state', 'in', ['sale', 'done'])
        ])

        # Sum up total ordered quantities per product
        ordered_qty_map = {}
        for order in orders:
            for line in order.order_line:
                product = line.product_id
                _logger.info("LINE PRODUCT: %s (%s)", product.name, product.type)
                if product.type == 'service':
                    continue
                pid = product.id
                ordered_qty_map[pid] = ordered_qty_map.get(pid, 0) + line.product_uom_qty

        # Sync to user inventory model
        for pid, total_ordered in ordered_qty_map.items():
            inventory_line = inventory_model.search([
                ('user_id', '=', user.id),
                ('product_id', '=', pid)
            ], limit=1)

            if inventory_line:
                inventory_line.write({
                    'total_ordered_qty': total_ordered
                })
            else:
                inventory_model.create({
                    'user_id': user.id,
                    'product_id': pid,
                    'current_qty': 0,  # start at 0
                    'total_ordered_qty': total_ordered
                })


        # Load updated inventory lines
        updated_inventory = inventory_model.search([('user_id', '=', user.id)])

        return request.render('user_inventory.portal_inventory_template', {
            'inventory': updated_inventory
        })

    @http.route(['/my/inventory/update'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_inventory_update(self, **post):
        user = request.env.user
        inventory_model = request.env['user.inventory.line'].sudo()

        for key, val in post.items():
            if key.startswith("qty_"):
                try:
                    line_id = int(key.replace("qty_", ""))
                    qty = int(val)
                    line = inventory_model.browse(line_id)
                    if line and line.user_id.id == user.id:
                        line.current_qty = qty
                except Exception as e:
                    _logger.warning(f"Error updating inventory line: {e}")

        return request.redirect('/my/inventory')
    
    @http.route(['/my/order/<int:order_id>/sync_inventory'], type='http', auth='user', website=True, csrf=True)
    def sync_inventory_from_order(self, order_id, **post):
        user = request.env.user
        order = request.env['sale.order'].sudo().browse(order_id)
        inventory_model = request.env['user.inventory.line'].sudo()

        if order.partner_id.id != user.partner_id.id or order.state not in ['sale', 'done']:
            return request.redirect('/my/orders')

        for line in order.order_line:
            product = line.product_id
            if product.type == 'service':
                continue
            pid = product.id
            ordered_qty = line.product_uom_qty

            inventory_line = inventory_model.search([
                ('user_id', '=', user.id),
                ('product_id', '=', pid)
            ], limit=1)

            if inventory_line:
                if ordered_qty > 0:
                    inventory_line.write({
                        'current_qty': inventory_line.current_qty + ordered_qty,
                    })
            else:
                inventory_model.create({
                    'user_id': user.id,
                    'product_id': pid,
                    'current_qty': ordered_qty,
                })

        return request.redirect(f'/my/orders/{order_id}')
