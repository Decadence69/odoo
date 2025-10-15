{
    'name': 'Portal Inventory Tracker',
    'version': '1.0',
    'category': 'Website',
    'author': 'Ivan Chen',
    'license': 'LGPL-3',
    'summary': 'Let users manage their inventory from the portal',
    'depends': ['sale', 'website_sale', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'security/user_inventory_rules.xml',
        'views/portal_inventory_template.xml',
        'views/portal_order_inherit.xml',
        'views/portal_my_orders_status.xml',
        'views/portal_inventory_entry.xml',
    ],
    'installable': True,
}
