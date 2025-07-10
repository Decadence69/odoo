{
    'name': 'Square Payment Provider',
    'author': 'Silver Touch Technologies Limited',
    'website': 'https://www.silvertouch.com',
    'version': '18.0.1.0',
    'category': 'Accounting/Payment Providers',
    'description': """Square Payment Provider for Odoo""",
    'depends': ['payment'],
    'data': [
        'data/payment_provider_data.xml',
        'views/payment_provider_views.xml',
        'views/payment_square_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sttl_payment_square/static/src/js/payment_form.js',
        ],
        'web.assets_backend': [
            'sttl_payment_square/static/src/js/payment_provider_form.js',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
    'auto_install': False,
}
