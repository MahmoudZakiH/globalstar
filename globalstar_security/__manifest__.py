# -*- coding: utf-8 -*-
{
    'name': "globalstar_security",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "IBS",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'stock', 'sale'],

    'data': [
        'security/group.xml',
        'demo/demo.xml',
        'views/views.xml',
    ],
}
