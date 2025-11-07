from odoo import models, fields, api

class EventApplication(models.Model):
    _inherit = 'event.application'
    
    # Add specialty and case tags to applications
    specialty_ids = fields.Many2many(
        'event.specialty',
        string='Specialties',
        help='Dental specialties covered in this event'
    )
    
    case_ids = fields.Many2many(
        'event.case',
        string='Cases',
        help='Types of cases covered in this event'
    )


class EventEvent(models.Model):
    _inherit = 'event.event'
    
    # Specialty - using tags (many2many) for flexibility
    specialty_ids = fields.Many2many(
        'event.specialty',
        string='Specialties',
        help='Dental specialties covered in this event'
    )
    
    # Cases - using tags (many2many) for flexibility
    case_ids = fields.Many2many(
        'event.case',
        string='Cases',
        help='Types of cases covered in this event'
    )

    country_id = fields.Many2one('res.country', string='Country')
    
    # Alternative: If you want dropdown selections instead of tags, use these:
    # specialty_id = fields.Many2one('event.specialty', string='Specialty')
    # case_id = fields.Many2one('event.case', string='Case')


class EventSpecialty(models.Model):
    _name = 'event.specialty'
    _description = 'Event Specialty'
    _order = 'name'
    
    name = fields.Char(string='Specialty Name', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Specialty name must be unique!')
    ]


class EventCase(models.Model):
    _name = 'event.case'
    _description = 'Event Case Type'
    _order = 'name'
    
    name = fields.Char(string='Case Type', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(default=True)
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Case type must be unique!')
    ]