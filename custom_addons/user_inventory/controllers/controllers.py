from odoo import http, _
from odoo.http import request
import logging
import re
from odoo import fields

_logger = logging.getLogger(__name__)

class PortalInventory(http.Controller):

    @http.route(['/my/inventory'], type='http', auth='user', website=True)
    def portal_inventory(self, **kw):
        user = request.env.user
        inventory_model = request.env['user.inventory.line'].sudo()
        product_options = request.env['product.product'].sudo().search([('sale_ok', '=', True)], limit=100)

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

        # _logger.info("RENDERING INVENTORY LINES")
        # for inv in updated_inventory:
        #     _logger.info("Line ID: %s | is_custom: %s | Product: %s | Custom Name: %s", inv.id, inv.is_custom, inv.product_id.name if inv.product_id else None, inv.custom_name)
        
        needs_reorder = bool(
            updated_inventory
            .filtered(lambda l: not l.is_custom and l.current_qty < (l.target_qty or 0))
        )
        return request.render('user_inventory.portal_inventory_template', {
            'inventory':      updated_inventory,
            'product_options': product_options,
            'needs_reorder':  needs_reorder,
        })



    @http.route(['/my/inventory/update'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_inventory_update(self, **post):
        user = request.env.user
        inventory_model = request.env['user.inventory.line'].sudo()

        for key, val in post.items():
            if key.startswith("qty_") or key.startswith("target_"):
                try:
                    line_id = int(key.split("_")[1])
                    line = inventory_model.browse(line_id)
                    if line and line.user_id.id == user.id:
                        if key.startswith("qty_"):
                            line.current_qty = int(val)
                        elif key.startswith("target_"):
                            line.target_qty = int(val)
                except Exception as e:
                    _logger.warning(f"Error updating inventory field {key}: {e}")


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

        return request.redirect(f'/my/inventory')

    @http.route(['/my/inventory/add_custom'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def add_custom_inventory(self, **post):
        user = request.env.user
        inventory_model = request.env['user.inventory.line'].sudo()

        name = post.get('custom_product_name')
        qty = int(post.get('custom_qty', 0))

        if name and qty >= 0:
            inventory_model.create({
                'user_id': user.id,
                'custom_name': name,
                'is_custom': True,
                'current_qty': qty,
            })

        return request.redirect('/my/inventory')

    @http.route(['/my/inventory/add_existing'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def add_existing_inventory(self, **post):
        user = request.env.user
        product_name = post.get('product_search', '').strip()
        qty = int(post.get('custom_qty', 0))

        _logger.info("ADDING EXISTING PRODUCT: %s | Qty: %s", product_name, qty)

        # Extract default_code from string like "[CODE] Name"
        match = re.match(r'\[(.*?)\]', product_name)
        code = match.group(1) if match else product_name.strip()

        product = request.env['product.product'].sudo().search([
            ('default_code', '=', code)
        ], limit=1)

        if not product:
            _logger.warning("Product not found with code: %s", code)
        else:
            inventory_model = request.env['user.inventory.line'].sudo()
            existing_line = inventory_model.search([
                ('user_id', '=', user.id),
                ('product_id', '=', product.id)
            ], limit=1)

            if existing_line:
                _logger.info("Existing line found. Updating qty...")
                existing_line.current_qty += qty
            else:
                _logger.info("Creating new inventory line...")
                inventory_model.create({
                    'user_id': user.id,
                    'product_id': product.id,
                    'current_qty': qty,
                    'total_ordered_qty': 0,
                })

        return request.redirect('/my/inventory')
    
    @http.route(['/my/inventory/reorder'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def reorder_from_inventory(self, **post):
        _logger.info("REORDER endpoint hit: %s", post)

        line_id = int(post.get('line_id', 0))
        inventory_line = request.env['user.inventory.line'].sudo().browse(line_id)

        if not inventory_line or inventory_line.is_custom:
            _logger.warning("Reorder skipped: invalid or custom line.")
            return request.redirect('/shop/cart')

        # Step 1: Extract SKU (e.g., [CONS_123])
        display_name = inventory_line.product_id.display_name or ''
        match = re.search(r'\[(.*?)\]', display_name)
        if not match:
            _logger.warning("Could not extract SKU from product name: %s", display_name)
            return request.redirect('/shop/cart')

        sku = match.group(1)
        _logger.info("Extracted SKU: %s", sku)

        # Step 2: Lookup product using default_code
        product = request.env['product.product'].sudo().search([
            ('default_code', '=', sku)
        ], limit=1)

        if not product:
            _logger.warning("No matching product for SKU: %s", sku)
            return request.redirect('/shop/cart')

        # Step 3: Compute reorder qty
        qty_to_add = inventory_line.target_qty - inventory_line.current_qty
        if qty_to_add <= 0:
            _logger.info("No reorder needed for line %s", line_id)
            return request.redirect('/shop/cart')

        # Step 4: Add to cart
        order = request.website.sale_get_order(force_create=True)
        order_line = request.env['sale.order.line'].sudo().search([
            ('order_id', '=', order.id),
            ('product_id', '=', product.id)
        ], limit=1)

        if order_line:
            order_line.product_uom_qty += qty_to_add
            _logger.info("Updated existing order line for product: %s", product.name)
        else:
            request.website.sale_get_order(force_create=True)._cart_update(
                product_id=product.id,
                add_qty=qty_to_add,
                set_qty=False
            )
            _logger.info("Created new order line for product: %s", product.name)

        return request.redirect('/my/inventory')
    
    @http.route(['/my/inventory/reorder_all'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def reorder_all(self, **post):
        user = request.env.user
        InventoryLine = request.env['user.inventory.line'].sudo()

        # 1) fetch all non-custom lines for this user
        all_lines = InventoryLine.search([
            ('user_id',   '=', user.id),
            ('is_custom', '=', False),
        ])
        # 2) filter those where current < target
        to_reorder = all_lines.filtered(lambda l: l.current_qty < (l.target_qty or 0))

        # 3) get or create the website order
        order = request.website.sale_get_order(force_create=True)

        # 4) loop & top-up each line
        for line in to_reorder:
            qty_to_add = line.target_qty - line.current_qty
            if qty_to_add <= 0:
                continue

            # if already in cart, bump qty; else create new
            existing = request.env['sale.order.line'].sudo().search([
                ('order_id',   '=', order.id),
                ('product_id', '=', line.product_id.id),
            ], limit=1)
            if existing:
                existing.product_uom_qty += qty_to_add
            else:
                order._cart_update(product_id=line.product_id.id, add_qty=qty_to_add)

        return request.redirect('/shop/cart')


