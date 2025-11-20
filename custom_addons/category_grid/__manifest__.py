{
    'name': 'Category Grid',
    'version': '18.0.1.0.0',
    'category': 'Website/Website',
    'summary': 'Display product categories in a grid layout',
    'description': """
        Display all product categories in a grid of cards
        similar to the shop design for easy navigation.
    """,
    'depends': ['website_sale'],
    'data': [
        'views/category_grid_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'category_grid/static/src/css/category_grid.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}