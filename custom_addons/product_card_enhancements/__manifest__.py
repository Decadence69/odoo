{
    'name': 'Product Card Enhancements',
    'version': '1.0',
    'category': 'Website',
    'summary': 'Makes product cards fully clickable and shows internal references',
    'description': """
        This module enhances the product display on the shop page:
        - Makes entire product cards clickable
        - Displays internal reference numbers as prefixes in product names
    """,
    'author': 'Ivan Chen',
    'depends': ['website_sale'],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'product_card_enhancements/static/src/js/product_card_click.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}