# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Dynamic Website Banner',
    'category': 'Website',
    'sequence': 10,
    'summary': 'Website,Banner',
    'version': '18.0.1.0',
    'author' : 'Ivan Chen',
    'description': """
        Adding time based website banner
        """,
    'depends': ['website', 'website_sale'],
    'assets': {
            'web.assets_frontend': [
                # inside .
                'website_banner/static/src/js/banner.js',
            ],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/website_banner.xml',
    ],
    'images': [],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
