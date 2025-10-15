from odoo import http, _
from odoo.http import request
import logging
import re
from odoo import fields
import json

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

        # Load updated inventory lines
        updated_inventory = inventory_model.search([('user_id', '=', user.id)], order='sequence, id')

        # Split into two buckets for the template
        official_inventory = updated_inventory.filtered(lambda l: bool(l.product_id))
        custom_inventory   = updated_inventory.filtered(lambda l: (l.is_custom or not l.product_id))

        # Reorder banner/flag should consider only product-linked items
        needs_reorder = bool(
            official_inventory.filtered(lambda l: l.current_qty < (l.target_qty or 0))
        )

        return request.render('user_inventory.portal_inventory_template', {
            # keep original var for backward-compat if your template still uses it anywhere
            'inventory':          updated_inventory,

            # new vars you’ll use to render two separate tables
            'official_inventory': official_inventory,
            'custom_inventory':   custom_inventory,

            'product_options':    product_options,
            'needs_reorder':      needs_reorder,

            # handy helpers if you want simple conditionals in the template
            'has_official':       bool(official_inventory),
            'has_custom':         bool(custom_inventory),
        })

    
    @http.route(['/my/inventory/update'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_inventory_update(self, **post):
        user = request.env.user
        inventory_model = request.env['user.inventory.line'].sudo()

        for key, val in post.items():
            if key.startswith("qty_") or key.startswith("target_") or key.startswith("sequence_"):
                try:
                    line_id = int(key.split("_")[1])
                    line = inventory_model.browse(line_id)
                    if line and line.user_id.id == user.id:
                        if key.startswith("qty_"):
                            line.current_qty = int(val)
                        elif key.startswith("target_"):
                            line.target_qty = int(val)
                        elif key.startswith("sequence_"):
                            line.sequence = int(val)
                except Exception as e:
                    _logger.warning(f"Error updating inventory field {key}: {e}")

        return request.redirect('/my/inventory')
    
    @http.route(['/my/order/<int:order_id>/sync_inventory'], type='http', auth='user', website=True, csrf=True)
    def sync_inventory_from_order(self, order_id, **post):
        user = request.env.user
        order = request.env['sale.order'].sudo().browse(order_id)

        # Basic guards
        if not order.exists() or order.partner_id.id != user.partner_id.id or order.state not in ['sale', 'done']:
            return request.redirect('/my/orders')

        # ✅ Idempotency guard: if already synced, just go to inventory
        if order.portal_inventory_synced:
            return request.redirect('/my/inventory')

        inventory_model = request.env['user.inventory.line'].sudo()

        # Perform sync
        for line in order.order_line:
            product = line.product_id
            if product.type == 'service':
                continue

            ordered_qty = line.product_uom_qty
            if not ordered_qty:
                continue

            inventory_line = inventory_model.search([
                ('user_id', '=', user.id),
                ('product_id', '=', product.id),
            ], limit=1)

            if inventory_line:
                inventory_line.write({
                    'current_qty': inventory_line.current_qty + ordered_qty,
                })
            else:
                inventory_model.create({
                    'user_id': user.id,
                    'product_id': product.id,
                    'current_qty': ordered_qty,
                })

        # ✅ Mark as synced so it can’t be applied again
        order.write({'portal_inventory_synced': True})

        # Redirect to inventory (or back to the order page if you prefer)
        return request.redirect('/my/inventory')

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

        line_id = int(post.get('line_id') or 0)
        if not line_id:
            return request.redirect('/shop/cart')

        website = request.website.sudo()
        company = website.company_id

        # Use company-aware proxies (no env(...) call)
        Line    = request.env['user.inventory.line'].sudo().with_context(allowed_company_ids=[company.id])
        Product = request.env['product.product'  ].sudo().with_context(allowed_company_ids=[company.id])
        SOL     = request.env['sale.order.line'  ].sudo().with_context(allowed_company_ids=[company.id])

        line = Line.browse(line_id)
        if not line or line.is_custom or not line.product_id:
            _logger.warning("Reorder skipped: invalid/custom line.")
            return request.redirect('/shop/cart')

        # Extract SKU [CODE] or fall back to the line.product_id
        display_name = line.product_id.display_name or ''
        m = re.search(r'\[(.*?)\]', display_name)
        product = False
        if m:
            sku = m.group(1)
            _logger.info("Extracted SKU: %s", sku)
            product = Product.search([
                ('default_code', '=', sku),
                '|', ('company_id', '=', False), ('company_id', '=', company.id),
            ], limit=1)
        if not product:
            product = line.product_id  # fallback

        # Basic guards
        if (not product) or (not product.sale_ok) or (product.type == 'service') or (not product.active):
            _logger.warning("Reorder skipped: product not found/saleable/service/archived.")
            return request.redirect('/shop/cart')

        qty_to_add = (line.target_qty or 0) - (line.current_qty or 0)
        if qty_to_add <= 0:
            _logger.info("No reorder needed for line %s", line_id)
            return request.redirect('/shop/cart')

        # Get/create cart *in this website company*
        order = website.with_context(allowed_company_ids=[company.id]).sale_get_order(force_create=True).sudo()
        if order.company_id != company:
            order = order.with_company(company)
            order.write({'company_id': company.id})

        # Align order parties to the commercial partner (no writes on partner record)
        commercial = request.env.user.partner_id.commercial_partner_id.sudo()
        vals = {}
        if order.partner_id != commercial:         vals['partner_id'] = commercial.id
        if order.partner_invoice_id != commercial: vals['partner_invoice_id'] = commercial.id
        if order.partner_shipping_id != commercial:vals['partner_shipping_id'] = commercial.id
        if vals: order.write(vals)

        # Upsert line
        existing = SOL.search([('order_id', '=', order.id), ('product_id', '=', product.id)], limit=1)
        if existing:
            existing.product_uom_qty += qty_to_add
            _logger.info("Updated existing SOL for %s (+%s)", product.display_name, qty_to_add)
        else:
            order._cart_update(product_id=product.id, add_qty=qty_to_add, set_qty=False)
            _logger.info("Created new SOL for %s (+%s)", product.display_name, qty_to_add)

        return request.redirect('/my/inventory')

    @http.route(['/my/inventory/reorder_all'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def reorder_all(self, **post):
        website = request.website.sudo()
        company = website.company_id

        Line = request.env['user.inventory.line'].sudo().with_context(allowed_company_ids=[company.id])
        SOL  = request.env['sale.order.line'  ].sudo().with_context(allowed_company_ids=[company.id])

        user = request.env.user
        lines = Line.search([('user_id', '=', user.id), ('is_custom', '=', False)])
        to_reorder = lines.filtered(lambda l: (l.current_qty or 0) < (l.target_qty or 0) and l.product_id and l.product_id.sale_ok and l.product_id.active and l.product_id.type != 'service')
        if not to_reorder:
            return request.redirect('/shop/cart')

        order = website.with_context(allowed_company_ids=[company.id]).sale_get_order(force_create=True).sudo()
        if order.company_id != company:
            order = order.with_company(company)
            order.write({'company_id': company.id})

        commercial = user.partner_id.commercial_partner_id.sudo()
        vals = {}
        if order.partner_id != commercial:         vals['partner_id'] = commercial.id
        if order.partner_invoice_id != commercial: vals['partner_invoice_id'] = commercial.id
        if order.partner_shipping_id != commercial:vals['partner_shipping_id'] = commercial.id
        if vals: order.write(vals)

        for l in to_reorder:
            add_qty = (l.target_qty or 0) - (l.current_qty or 0)
            if add_qty <= 0:
                continue
            existing = SOL.search([('order_id', '=', order.id), ('product_id', '=', l.product_id.id)], limit=1)
            if existing:
                existing.product_uom_qty += add_qty
            else:
                order._cart_update(product_id=l.product_id.id, add_qty=add_qty)
        return request.redirect('/shop/cart')


    @http.route(['/my/inventory/delete'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def delete_inventory_line(self, **post):
        """Delete an inventory line"""
        user = request.env.user
        line_id = int(post.get('line_id', 0))
        
        if not line_id:
            _logger.warning("No line_id provided for deletion")
            return request.redirect('/my/inventory')
        
        inventory_line = request.env['user.inventory.line'].sudo().browse(line_id)
        
        # Security check: ensure the line belongs to the current user
        if not inventory_line or inventory_line.user_id.id != user.id:
            _logger.warning("Unauthorized delete attempt for line %s by user %s", line_id, user.id)
            return request.redirect('/my/inventory')
        
        try:
            inventory_line.unlink()
            _logger.info("Successfully deleted inventory line %s for user %s", line_id, user.id)
        except Exception as e:
            _logger.error("Error deleting inventory line %s: %s", line_id, e)
        
        return request.redirect('/my/inventory')

    @http.route(['/my/inventory/update_sequence'], type='json', auth='user', methods=['POST'], website=True, csrf=False)
    def update_inventory_sequence(self, **post):
        user = request.env.user
        inventory_model = request.env['user.inventory.line'].sudo()
        
        line_ids = post.get('line_ids', [])
        
        for index, line_id in enumerate(line_ids):
            line = inventory_model.browse(int(line_id))
            if line and line.user_id.id == user.id:
                line.sequence = (index + 1) * 10
        
        return {'success': True}
