# -*- coding: utf-8 -*-
{
    'name': 'Website Sale Customization',
    'version': '1.1',
    'category': 'Website/Website',
    'summary': 'Add Go to My Orders button, remove on hover picture zoom, and a back button',
    'depends': ['website_sale'],
    'data': [
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_uiux/static/src/css/product_image.css',
            'website_uiux/static/src/js/disable_zoom.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}