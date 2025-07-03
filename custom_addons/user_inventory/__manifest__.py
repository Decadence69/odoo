{
    'name': 'Portal Inventory Tracker',
    'version': '1.0',
    'category': 'Website',
    'author': 'Ivan Chen',
    'summary': 'Let users manage their inventory from the portal',
    'depends': ['website_sale', 'portal'],
    'data': [
        'views/portal_inventory_template.xml',
        'views/portal_order_inherit.xml',
    ],
    'installable': True,
}
