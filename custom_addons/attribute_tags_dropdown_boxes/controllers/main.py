# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class WebsiteSaleFilters(http.Controller):
    
    @http.route('/shop/filters/batch_validate', type='json', auth='public', website=True, csrf=False)
    def batch_validate_filters(self, current_filters=None, check_filters=None, path=None, **kwargs):
        """
        Validates multiple filter combinations in a single request.
        
        Args:
            current_filters: Dict with keys: tags, attributes, search, category
            check_filters: List of dicts with 'name' and 'value' keys
            path: Current URL path
            
        Returns:
            Dict with 'valid_combinations' mapping "name:value" to True/False
        """
        _logger.info("=" * 80)
        _logger.info("BATCH VALIDATE FILTERS CALLED")
        _logger.info("=" * 80)
        
        try:
            _logger.info(f"current_filters: {current_filters}")
            _logger.info(f"check_filters: {check_filters}")
            _logger.info(f"path: {path}")
            _logger.info(f"kwargs: {kwargs}")
            
            # Simple test to make sure we can return data
            test_result = {
                'valid_combinations': {
                    'test:123': True,
                    'test:456': False
                }
            }
            _logger.info(f"TEST: About to return {test_result}")
            
            if not check_filters:
                _logger.warning("No check_filters provided - returning empty")
                return {'valid_combinations': {}}
            
            _logger.info(f"Processing {len(check_filters)} filters")
            
            current_filters = current_filters or {}
            current_tags = current_filters.get('tags', [])
            current_attrs = current_filters.get('attributes', [])
            search_term = current_filters.get('search', '')
            category_id = current_filters.get('category', '')
            
            _logger.info(f"Parsed - tags: {current_tags}, attrs: {current_attrs}")
            
            # Get base domain for current context
            base_domain = self._get_base_domain(path, category_id, search_term)
            _logger.info(f"Base domain: {base_domain}")
            
            # Count products with base domain
            try:
                base_count = request.env['product.template'].search_count(base_domain)
                _logger.info(f"Base domain matches {base_count} products")
            except Exception as e:
                _logger.error(f"Error counting base products: {e}")
                base_count = 0
            
            valid_combinations = {}
            
            # Check each filter option
            for idx, filter_item in enumerate(check_filters):
                name = filter_item.get('name')
                value = filter_item.get('value')
                
                _logger.info(f"[{idx+1}/{len(check_filters)}] Processing filter: name={name}, value={value}")
                
                if not name or not value:
                    _logger.warning(f"Skipping invalid filter: {filter_item}")
                    continue
                
                key = f"{name}:{value}"
                
                # Build test domain with this filter added
                test_domain = base_domain.copy()
                
                if name == 'tags':
                    # OR logic within tags: add this tag to current tags
                    test_tags = list(current_tags) if current_tags else []
                    if value not in test_tags:
                        test_tags.append(value)
                    
                    if test_tags:
                        # Convert to integers
                        tag_ids = []
                        for t in test_tags:
                            try:
                                tag_ids.append(int(t))
                            except (ValueError, TypeError):
                                _logger.warning(f"Invalid tag ID: {t}")
                        
                        if tag_ids:
                            # Tags use OR logic within themselves
                            tag_domain = [('public_categ_ids.id', 'in', tag_ids)]
                            test_domain.extend(tag_domain)
                            _logger.info(f"  Added tag domain: {tag_domain}")
                    
                    # AND logic: apply current attribute filters
                    if current_attrs:
                        attr_domain = self._build_attribute_domain(current_attrs)
                        test_domain.extend(attr_domain)
                        _logger.info(f"  Added attribute domain: {attr_domain}")
                
                elif name == 'attribute_value':
                    # Apply current tags (AND logic)
                    if current_tags:
                        tag_ids = []
                        for t in current_tags:
                            try:
                                tag_ids.append(int(t))
                            except (ValueError, TypeError):
                                _logger.warning(f"Invalid tag ID: {t}")
                        
                        if tag_ids:
                            tag_domain = [('public_categ_ids.id', 'in', tag_ids)]
                            test_domain.extend(tag_domain)
                            _logger.info(f"  Added tag domain: {tag_domain}")
                    
                    # OR logic within same attribute, AND logic between attributes
                    test_attrs = list(current_attrs) if current_attrs else []
                    if value not in test_attrs:
                        test_attrs.append(value)
                    
                    if test_attrs:
                        attr_domain = self._build_attribute_domain(test_attrs)
                        test_domain.extend(attr_domain)
                        _logger.info(f"  Added attribute domain: {attr_domain}")
                
                # Log final test domain
                _logger.info(f"  Final test domain: {test_domain}")
                
                # Check if any products match this combination
                try:
                    product_count = request.env['product.template'].with_context(bin_size=True).search_count(test_domain)
                    valid_combinations[key] = product_count > 0
                    _logger.info(f"  Result: {product_count} products -> valid={valid_combinations[key]}")
                except Exception as e:
                    _logger.error(f"  Error checking products for {key}: {str(e)}", exc_info=True)
                    valid_combinations[key] = True  # Default to showing the filter on error
                
            _logger.info("=" * 80)
            _logger.info(f"BATCH VALIDATE COMPLETE - Returning {len(valid_combinations)} results")
            _logger.info(f"Results: {valid_combinations}")
            _logger.info("=" * 80)
            
            return {'valid_combinations': valid_combinations}
            
        except Exception as e:
            _logger.error("=" * 80)
            _logger.error(f"EXCEPTION in batch_validate_filters: {str(e)}", exc_info=True)
            _logger.error("=" * 80)
            return {'valid_combinations': {}}
    
    def _get_base_domain(self, path, category_id, search_term):
        """Build base domain from current context (category, search, etc.)"""
        domain = [
            ('sale_ok', '=', True),
            ('website_published', '=', True),
        ]
        
        # Add category filter if present
        if category_id and str(category_id).isdigit():
            domain.append(('public_categ_ids', 'child_of', int(category_id)))
        
        # Add search filter if present
        if search_term:
            domain.append('|')
            domain.append(('name', 'ilike', search_term))
            domain.append(('description_sale', 'ilike', search_term))
        
        return domain
    
    def _build_attribute_domain(self, attribute_values):
        """
        Build domain for attributes with OR within same attribute, AND between different attributes.
        
        Args:
            attribute_values: List of strings like "1-5" (attribute_id-value_id)
        
        Returns:
            List domain
        """
        # Group by attribute ID
        attrs_by_id = {}
        for attr_val in attribute_values:
            if not attr_val or '-' not in str(attr_val):
                continue
            
            parts = str(attr_val).split('-', 1)
            if len(parts) != 2:
                continue
            
            attr_id_str, val_id_str = parts
            if not attr_id_str.isdigit() or not val_id_str.isdigit():
                continue
            
            attr_id = int(attr_id_str)
            val_id = int(val_id_str)
            
            if attr_id not in attrs_by_id:
                attrs_by_id[attr_id] = []
            attrs_by_id[attr_id].append(val_id)
        
        if not attrs_by_id:
            return []
        
        # Build domain with OR within same attribute, AND between attributes
        domain = []
        for attr_id, value_ids in attrs_by_id.items():
            if len(value_ids) == 1:
                # Single value for this attribute
                domain.append(('attribute_line_ids.value_ids', 'in', value_ids))
            else:
                # Multiple values for same attribute (OR logic)
                # Add OR prefix for all values of this attribute
                for _ in range(len(value_ids) - 1):
                    domain.append('|')
                for val_id in value_ids:
                    domain.append(('attribute_line_ids.value_ids', '=', val_id))
        
        return domain