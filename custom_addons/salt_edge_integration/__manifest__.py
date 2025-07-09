{
    'name': 'Salt Edge Integration',
    'version': '1.0',
    'summary': 'Integrate Salt Edge open banking with Odoo',
    'depends': ['payment', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/salt_edge_views.xml',
        'views/sync_wizard_view.xml',
        'data/payment_provider.xml',
        'data/payment_acquirer.xml'
    ],
    'installable': True,
    'application': True,
}
