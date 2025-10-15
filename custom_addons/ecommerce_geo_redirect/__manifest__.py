{
    'name': 'GeoLite2 Geographic Redirect',
    'version': '1.0.0',
    'category': 'Website',
    'summary': 'Redirect users to country-specific websites based on IP geolocation',
    'description': """
        Geographic Redirect Module
        ==========================
        Automatically redirects website visitors to their country-specific subdomain
        based on their IP address using GeoLite2 database.
        
        Features:
        - Automatic country detection via IP
        - Configurable country-to-subdomain mapping
        - Session-based redirect (only once per session)
        - Admin interface for managing redirects
    """,
    'author': 'Ivan Chen',
    'depends': ['website', 'website_sale'],
    'external_dependencies': {
        'python': ['geoip2', 'requests'],
    },
    'data': [
        'views/geo_redirect_config_views.xml',
        'views/geo_database_updater_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}