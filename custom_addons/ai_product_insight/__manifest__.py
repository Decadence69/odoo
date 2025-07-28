{
    'name': 'AI Product Insights',
    'version': '1.0',
    'category': 'Website',
    'summary': 'AI-powered product insights using Google Gemini',
    'description': 'Adds AI insight buttons to product catalog and pages',
    'depends': ['website_sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/shop_templates.xml',
        # 'views/assets.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'ai_product_insight/static/src/css/ai_insights.css',
        ],
        'web.assets_frontend': [
            'ai_product_insight/static/src/js/ai_insights.js',
            'ai_product_insight/static/src/css/ai_insights.css',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
