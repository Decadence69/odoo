{
    'name': 'Dentist Specialty Signup',
    'version': '18.0.1.0.0',
    'category': 'Website',
    'summary': 'Add specialty selection for dentist signup using Job Position',
    'description': """
        Allows dentists to select their specialty during signup using the Job Position field
    """,
    'depends': ['base', 'auth_signup', 'website'],
    'data': [
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}