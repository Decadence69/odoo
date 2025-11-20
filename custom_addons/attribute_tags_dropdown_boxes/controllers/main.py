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
        """
        try:
            if not check_filters:
                _logger.warning("No check_filters provided")
                return {'valid_combinations': {}}
            
            current_filters = current_filters or {}
            current_tags = current_filters.get('tags', [])
            current_attrs = current_filters.get('attributes', [])
            search_term = current_filters.get('search', '')
            category_id = current_filters.get('category', '')
            
            # Get base domain for current context
            base_domain = self._get_base_domain(path, category_id, search_term)
            
            valid_combinations = {}
            
            # Group filters by attribute to check within same attribute
            filters_by_attribute = {}
            tag_filters = []
            
            for filter_item in check_filters:
                name = filter_item.get('name')
                value = filter_item.get('value')
                
                if not name or not value:
                    continue
                
                if name == 'tags':
                    tag_filters.append(value)
                elif name == 'attribute_value' and '-' in str(value):
                    attr_id = str(value).split('-')[0]
                    if attr_id not in filters_by_attribute:
                        filters_by_attribute[attr_id] = []
                    filters_by_attribute[attr_id].append(value)
            
            # Check each filter option
            for filter_item in check_filters:
                name = filter_item.get('name')
                value = filter_item.get('value')
                
                if not name or not value:
                    continue
                
                key = f"{name}:{value}"
                
                # Build test domain AS IF this filter is selected
                test_domain = base_domain.copy()
                
                if name == 'tags':
                    # Test: What if we ADD this tag to current tags?
                    test_tags = list(current_tags) if current_tags else []
                    if value not in test_tags:
                        test_tags.append(value)
                    
                    if test_tags:
                        tag_ids = [int(t) for t in test_tags if str(t).isdigit()]
                        if tag_ids:
                            # Tags: OR logic (any tag matches)
                            test_domain.append(('public_categ_ids.id', 'in', tag_ids))
                    
                    # Apply current attribute filters (AND logic with tags)
                    if current_attrs:
                        attr_domain = self._build_attribute_domain(current_attrs)
                        test_domain.extend(attr_domain)
                
                elif name == 'attribute_value':
                    # Apply current tags first (AND logic)
                    if current_tags:
                        tag_ids = [int(t) for t in current_tags if str(t).isdigit()]
                        if tag_ids:
                            test_domain.append(('public_categ_ids.id', 'in', tag_ids))
                    
                    # Check if selecting THIS value within its attribute group
                    # while keeping OTHER attribute groups as-is
                    if not value or '-' not in str(value):
                        continue
                    
                    this_attr_id = str(value).split('-')[0]
                    test_attrs = []
                    
                    # Keep all attributes from OTHER attribute groups
                    for attr in current_attrs:
                        if str(attr).split('-')[0] != this_attr_id:
                            test_attrs.append(attr)
                    
                    # For THIS attribute group, ONLY include the value we're testing
                    test_attrs.append(value)
                    
                    if test_attrs:
                        attr_domain = self._build_attribute_domain(test_attrs)
                        test_domain.extend(attr_domain)
                
                # Check if any products match
                try:
                    product_count = request.env['product.template'].with_context(bin_size=True).search_count(test_domain)
                    valid_combinations[key] = product_count > 0
                    
                except Exception as e:
                    _logger.error(f"Error checking {key}: {str(e)}")
                    valid_combinations[key] = True  # Default to showing on error
            
            return {'valid_combinations': valid_combinations}
            
        except Exception as e:
            _logger.error(f"Exception in batch_validate_filters: {str(e)}", exc_info=True)
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
                # Need to add OR operators before the conditions
                for i in range(len(value_ids) - 1):
                    domain.append('|')
                
                for val_id in value_ids:
                    domain.append(('attribute_line_ids.value_ids', '=', val_id))
        
        return domain