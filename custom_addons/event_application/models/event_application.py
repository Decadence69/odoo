from odoo import models, fields, api

class EventApplication(models.Model):
    _name = 'event.application'
    _description = 'Event Application'
    _order = 'create_date desc'
    
    name = fields.Char(string='Event Name', required=True)
    partner_id = fields.Many2one('res.partner', string='Organizer', required=True, default=lambda self: self.env.user.partner_id.id)
    date_begin = fields.Datetime(string='Start Date', required=True)
    date_end = fields.Datetime(string='End Date', required=True)
    description = fields.Html(string='Description')
    location = fields.Char(string='Location')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('published', 'Published')
    ], default='draft', string='Status', required=True)
    
    # Add specialty and case tags
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
    
    rejection_reason = fields.Text(string='Rejection Reason')
    event_id = fields.Many2one('event.event', string='Published Event', readonly=True)
    
    # Portal access fields
    access_url = fields.Char('Portal Access URL', compute='_compute_access_url')
    
    def _compute_access_url(self):
        """Generate portal URL"""
        for application in self:
            application.access_url = f'/my/event/application/{application.id}'
    
    def action_submit(self):
        self.state = 'submitted'
        
    def action_approve(self):
        self.state = 'approved'
        
    def action_reject(self):
        """Open wizard for rejection reason"""
        return {
            'name': 'Reject Application',
            'type': 'ir.actions.act_window',
            'res_model': 'reject.application.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_application_id': self.id}
        }
    
    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({
            'state': 'draft',
            'rejection_reason': False
        })
        
    def action_publish(self):
        """Create the actual event record on the website"""
        self.ensure_one()
        event = self.env['event.event'].create({
            'name': self.name,
            'date_begin': self.date_begin,
            'date_end': self.date_end,
            'description': self.description,
            'location': self.location,
            'address_id': self.partner_id.id,
            'organizer_id': self.partner_id.id,
            'is_published': True,
            'user_id': self.env.user.id,
            'application_id': self.id,
            'specialty_ids': [(6, 0, self.specialty_ids.ids)],  # Transfer specialty tags
            'case_ids': [(6, 0, self.case_ids.ids)],  # Transfer case tags
        })
        self.write({
            'state': 'published',
            'event_id': event.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'event.event',
            'res_id': event.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_open_event(self):
        """Open the published event"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'event.event',
            'res_id': self.event_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class EventEvent(models.Model):
    _inherit = 'event.event'
    
    application_id = fields.Many2one('event.application', string='Original Application', readonly=True)
    location = fields.Char(string='Location')
    
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
    
    def action_view_registrations_portal(self):
        """Allow organizers to view registrations"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Event Registrations',
            'res_model': 'event.registration',
            'view_mode': 'list,form',
            'domain': [('event_id', '=', self.id)],
            'context': {'default_event_id': self.id}
        }


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
    

class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def action_mark_attended(self):
        """Mark attendee as attended (same as barcode scan)"""
        self.write({'state': 'done'})
    
    def action_mark_not_attended(self):
        """Mark attendee as not attended"""
        self.write({'state': 'open'})
    
    def is_attended(self):
        """Check if registration is marked as attended"""
        return self.state == 'done'