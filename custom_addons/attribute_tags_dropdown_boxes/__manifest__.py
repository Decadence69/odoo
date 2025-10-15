{
    'name': 'Product Dropdown Filters',
    'version': '1.0',
    'category': 'Website/Website',
    'summary': 'Convert product filters to dropdown with multi-select checkboxes',
    'description': """
        Product Dropdown Filters
        ========================
        This module converts the default checkbox filters on the shop page
        into dropdown menus with multi-select capability.
        
        Features:
        ---------
        * Multi-select dropdown filters for product attributes
        * Multi-select dropdown filters for product tags
        * Clean URL management
        * Apply filters button
        * Clear all option
        * Persistent filter state after page reload
        * Theme-aware styling
    """,
    'author': 'Ivan Chen',
    'depends': ['website_sale'],
    'data': [],
    'assets': {
        'web.assets_frontend': [
            'attribute_tags_dropdown_boxes/static/src/css/dropdown_filters.css',
            'attribute_tags_dropdown_boxes/static/src/js/dropdown_filters.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
