# -*- coding: utf-8 -*-
{
    'name': 'Auth Signup Email Verification',
    'version': '18.0.1.0.6',
    'category': 'Website/Website',
    'summary': 'Email verification for signup with company/individual selection',
    'description': """
        This module enhances the standard Odoo signup process by adding:
        * Email verification before account activation
        * Company/Individual account type selection
        * Dynamic field selection from any model
        * Configurable verification link validity
        * Integration with Odoo's official signup settings
    """,
    'author': 'INTERCOM MALI',
    'website': 'https://intercom.ml',
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
    ],
    'depends': [
        'auth_signup',
        'portal',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/email_templates.xml',
        'views/signup_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
    'price': .0,
    'currency': 'EUR',
} 