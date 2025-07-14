{
    'name': 'Multi Currency Database Modifier',
    'version': '1.0',
    'summary': 'Adds original and MYR-converted sales amounts to Sales Orders',
    'description': 'Stores both the original transaction amount and the converted amount in MYR on sale orders.',
    'author': 'Mr Bur Malaysia',
    'depends': ['sale_management', 'account'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
