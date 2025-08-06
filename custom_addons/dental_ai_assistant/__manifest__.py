{
    'name': 'Dental AI Assistant',
    'version': '18.0.1.0.0',
    'depends': ['base', 'web'],
    'external_dependencies': {
        'python': ['chromadb', 'sentence_transformers', 'google-generativeai', 'numpy', 'pandas'],
    },
    'data': [
        'views/dental_ai_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'dental_ai_assistant/static/src/js/dental_ai_widget.js',
            'dental_ai_assistant/static/src/css/dental_ai.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}