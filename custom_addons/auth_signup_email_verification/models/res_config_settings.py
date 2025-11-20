# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
import json


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Basic module settings
    auth_signup_company_toggle = fields.Boolean(
        string='Allow Company/Individual Selection',
        help='Enable users to choose between Individual and Company account types during signup',
        config_parameter='auth_signup_email_verification.company_toggle'
    )
    
    auth_signup_verification_validity_hours = fields.Integer(
        string='Email Verification Validity (Hours)',
        help='Number of hours the verification link remains valid',
        config_parameter='auth_signup_email_verification.verification_validity_hours',
        default=144  # 6 days
    )
    
    # Simplified single container approach - avoid custom relation tables
    selected_model = fields.Selection(
        selection='_get_available_models_selection',
        string='Select Model',
        help='Choose a model to configure fields for'
    )
    
    # Store selected field IDs as JSON string to avoid relation table issues
    selected_field_ids_json = fields.Char(
        string='Selected Field IDs (JSON)',
        help='JSON string of selected field IDs for current model'
    )
    
    # All configurations storage
    all_field_configurations = fields.Char(
        string='All Field Configurations',
        help='JSON string storing field selections for all models',
        config_parameter='auth_signup_email_verification.all_field_configurations'
    )
    
    # Computed fields for display - no relation tables
    available_field_ids = fields.Many2many(
        'ir.model.fields',
        string='Available Fields',
        compute='_compute_available_field_ids',
        help='Available fields for the selected model'
    )
    
    selected_signup_field_ids = fields.Many2many(
        'ir.model.fields',
        string='Fields to Show During Signup',
        compute='_compute_selected_signup_field_ids',
        inverse='_inverse_selected_signup_field_ids',
        help='Select which fields to display during signup'
    )
    
    # Summary display
    configuration_summary = fields.Html(
        string='Configuration Summary',
        compute='_compute_configuration_summary',
        help='Summary of all configured model fields'
    )
    
    @api.model
    def _get_available_models_selection(self):
        """Get available models for selection - DYNAMIC loading"""
        try:
            # Get all models from ir.model that are suitable for signup
            model_records = self.env['ir.model'].search([
                ('transient', '=', False),  # Skip transient models
                ('abstract', '=', False),   # Skip abstract models
            ], order='display_name')
            
            verified_models = []
            
            # Priority models (always show first if available)
            priority_models = [
                'res.partner', 'crm.lead', 'sale.order', 'product.product', 
                'res.company', 'account.move', 'project.project', 'hr.employee'
            ]
            
            # Add priority models first
            for model_record in model_records:
                if model_record.model in priority_models:
                    try:
                        if model_record.model in self.env.registry:
                            model = self.env[model_record.model]
                            model._fields  # Test accessibility
                            verified_models.append((model_record.model, model_record.display_name))
                    except Exception:
                        continue
            
            # Add other suitable models (excluding technical ones)
            excluded_prefixes = [
                'ir.', 'base.', 'res.config', 'wizard.', 'report.', 'mail.template',
                'mail.compose', 'account.report', 'account.aged', 'account.bank',
                'account.dashboard', 'account.invoice.send', 'pos.', 'website.',
                'payment.', 'stock.report', 'sale.report', 'purchase.report'
            ]
            
            for model_record in model_records:
                # Skip if already added or excluded
                if (model_record.model in [m[0] for m in verified_models] or
                    any(model_record.model.startswith(prefix) for prefix in excluded_prefixes)):
                    continue
                
                try:
                    if model_record.model in self.env.registry:
                        model = self.env[model_record.model]
                        # Check if model has basic fields (not just technical ones)
                        basic_fields = [f for f in model._fields.keys() 
                                      if not f.startswith('_') and f not in ['id', 'create_date', 'write_date']]
                        if len(basic_fields) > 3:  # Only include if has meaningful fields
                            verified_models.append((model_record.model, model_record.display_name))
                except Exception:
                    continue
            
            # Ensure we always have at least some models
            if not verified_models:
                verified_models = [
                    ('res.partner', 'Contact'),
                    ('crm.lead', 'Lead/Opportunity'),
                ]
            
            # Keep only Contact model
            contact_models = [model for model in verified_models if model[0] == 'res.partner']
            return contact_models if contact_models else [('res.partner', 'Contact')]
            
        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error loading dynamic models: {str(e)}")
            # Safe fallback - only Contact
            return [('res.partner', 'Contact')]
    
    @api.depends('selected_model')
    def _compute_available_field_ids(self):
        """Compute available fields for the selected model"""
        for record in self:
            if record.selected_model:
                try:
                    # Get the model
                    model_obj = self.env['ir.model'].search([('model', '=', record.selected_model)], limit=1)
                    
                    if model_obj:
                        # Get suitable fields for signup - DYNAMIC and comprehensive
                        suitable_fields = self.env['ir.model.fields'].sudo().search([
                            ('model_id', '=', model_obj.id),
                            ('ttype', 'in', [
                                'char', 'text', 'html', 'selection', 'boolean', 
                                'integer', 'float', 'monetary', 'date', 'datetime',
                                'many2one', 'one2many', 'many2many', 'binary', 'image'
                            ]),
                            ('name', 'not in', [
                                'id', 'create_date', 'write_date', 'create_uid', 'write_uid', 
                                '__last_update', 'display_name', 'active', 'sequence',
                                'message_ids', 'message_follower_ids', 'activity_ids',
                                'message_main_attachment_id', 'website_message_ids'
                            ]),
                            ('compute', '=', False),  # Exclude computed fields
                            ('store', '=', True),     # Only stored fields
                            ('readonly', '=', False), # Exclude readonly fields
                        ], order='field_description')
                        record.available_field_ids = suitable_fields
                    else:
                        record.available_field_ids = False
                except Exception:
                    record.available_field_ids = False
            else:
                record.available_field_ids = False
    @api.depends('selected_model', 'all_field_configurations', 'selected_field_ids_json')
    def _compute_selected_signup_field_ids(self):
        """Compute selected fields from configurations"""
        for record in self:
            if record.selected_model:
                try:
                    # First try to get from temporary JSON (for current session)
                    if record.selected_field_ids_json:
                        field_ids = json.loads(record.selected_field_ids_json)
                        fields = self.env['ir.model.fields'].browse(field_ids)
                        record.selected_signup_field_ids = fields
                        continue
                    
                    # Then try to get from saved configurations
                    all_configs = json.loads(record.all_field_configurations or '{}')
                    field_names = all_configs.get(record.selected_model, [])
                    
                    if field_names:
                        model_obj = self.env['ir.model'].search([('model', '=', record.selected_model)], limit=1)
                        if model_obj:
                            # Get all matching fields first
                            all_fields = self.env['ir.model.fields'].search([
                                ('model_id', '=', model_obj.id),
                                ('name', 'in', field_names)
                            ])
                            
                            # ✅ PRESERVE ORDER: Manually sort to match field_names order  
                            field_dict = {field.name: field for field in all_fields}
                            ordered_fields = self.env['ir.model.fields']
                            for field_name in field_names:  # Use stored JSON order!
                                if field_name in field_dict:
                                    ordered_fields |= field_dict[field_name]
                            
                            record.selected_signup_field_ids = ordered_fields
                            # Store in JSON for consistency
                            record.selected_field_ids_json = json.dumps(ordered_fields.ids)
                        else:
                            record.selected_signup_field_ids = False
                    else:
                        record.selected_signup_field_ids = False
                except (json.JSONDecodeError, Exception):
                    record.selected_signup_field_ids = False
            else:
                record.selected_signup_field_ids = False
    
    def _inverse_selected_signup_field_ids(self):
        """Store selected field IDs in JSON format"""
        for record in self:
            if record.selected_signup_field_ids:
                record.selected_field_ids_json = json.dumps(record.selected_signup_field_ids.ids)
            else:
                record.selected_field_ids_json = '[]'

    @api.depends('all_field_configurations')
    def _compute_configuration_summary(self):
        """Generate HTML summary of all configured models and fields"""
        for record in self:
            try:
                all_configs = json.loads(record.all_field_configurations or '{}')
                if not all_configs:
                    record.configuration_summary = "<p class='text-muted'><i class='fa fa-info-circle'></i> No models configured yet.</p>"
                    continue
                
                # Create enhanced model cards with better UX
                model_blocks_html = ""
                total_fields = 0
                
                for model_name, field_names in all_configs.items():
                    # Get model display name safely
                    model_obj = self.env['ir.model'].search([('model', '=', model_name)], limit=1)
                    model_display = model_obj.name if model_obj else model_name
                    
                    field_count = len(field_names)
                    total_fields += field_count
                    
                    # Create field list as proper HTML list
                    field_list_html = ""
                    for index, field_name in enumerate(field_names, 1):
                        # Get field display name if possible
                        field_obj = self.env['ir.model.fields'].search([
                            ('model_id', '=', model_obj.id if model_obj else False),
                            ('name', '=', field_name)
                        ], limit=1)
                        field_display = field_obj.field_description if field_obj else field_name
                        
                        field_list_html += f"""
                        <li style='
                            font-size: 11px; color: #495057; padding: 4px 0; 
                            border-bottom: 1px solid #f8f9fa; line-height: 1.4;
                            display: flex; align-items: center; justify-content: space-between;
                        '>
                            <div style='display: flex; align-items: center;'>
                                <span style='
                                    background: #28a745; color: white; font-weight: bold; 
                                    border-radius: 50%; width: 18px; height: 18px; 
                                    display: flex; align-items: center; justify-content: center; 
                                    font-size: 10px; margin-right: 8px;
                                '>{index}</span>
                                <strong>{field_display}</strong>
                                <small style='color: #868e96; margin-left: 6px;'>({field_name})</small>
                            </div>
                            <i class='fa fa-arrows-v text-muted' style='font-size: 10px;' title='Signup form order'></i>
                        </li>
                        """
                    
                    # Choose icon based on model type
                    model_icon = "fa-users" if "partner" in model_name else \
                               "fa-shopping-cart" if "sale" in model_name else \
                               "fa-cube" if "product" in model_name else \
                               "fa-file-text-o" if "lead" in model_name else "fa-database"
                    
                    model_blocks_html += f"""
                    <div class='model-card' style='
                        min-width: 280px; max-width: 280px; margin-right: 16px; 
                        border: 1px solid #e1e8ed; border-radius: 8px; padding: 16px; 
                        background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%); 
                        flex-shrink: 0; cursor: pointer; transition: all 0.3s ease;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                    ' onmouseover='this.style.transform="translateY(-2px)"; this.style.boxShadow="0 4px 16px rgba(0,0,0,0.12)";' 
                      onmouseout='this.style.transform="translateY(0)"; this.style.boxShadow="0 2px 8px rgba(0,0,0,0.06)";'>
                        
                        <div style='display: flex; align-items: center; margin-bottom: 12px;'>
                            <i class='fa {model_icon}' style='color: #6c757d; font-size: 18px; margin-right: 10px;'></i>
                            <div style='flex: 1;'>
                                <div style='font-weight: 600; color: #495057; font-size: 14px; line-height: 1.2; margin-bottom: 3px;'>
                                    {model_display}
                                </div>
                                <div style='font-size: 11px; color: #868e96; text-transform: uppercase; letter-spacing: 0.5px;'>
                                    {model_name}
                                </div>
                            </div>
                        </div>
                        
                        <div style='margin-bottom: 12px;'>
                            <span style='
                                display: inline-block; background: #e3f2fd; color: #1976d2; 
                                padding: 4px 10px; border-radius: 12px; font-size: 11px; 
                                font-weight: 500; margin-bottom: 8px;
                            '>
                                <i class='fa fa-list-alt' style='margin-right: 4px;'></i>
                                {field_count} fields configured
                            </span>
                        </div>
                        
                        <div style='margin-bottom: 12px;'>
                            <div style='font-weight: 600; color: #495057; font-size: 12px; margin-bottom: 6px;'>
                                <i class='fa fa-cogs' style='margin-right: 4px; color: #28a745;'></i>
                                Configured Fields:
                            </div>
                            <ul style='
                                margin: 0; padding: 0; list-style: none; 
                                max-height: 120px; overflow-y: auto; 
                                border: 1px solid #f1f3f4; border-radius: 4px; 
                                background: #fafbfc; padding: 6px;
                            '>
                                {field_list_html}
                            </ul>
                        </div>
                        
                    </div>
                    """
                
                # Clean, contained layout within the purple card
                summary_html = f"""
                <div style='width: 100%;'>
                    
                    <!-- Stats Header -->
                    <div style='margin-bottom: 16px; padding: 12px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 8px; border: 1px solid #dee2e6;'>
                        <div style='display: flex; align-items: center; justify-content: space-between;'>
                            <div style='display: flex; align-items: center;'>
                                <i class='fa fa-database' style='color: #495057; font-size: 18px; margin-right: 8px;'></i>
                                <span style='font-weight: 600; color: #495057; font-size: 14px;'>Configured Models</span>
                            </div>
                            <div style='display: flex; gap: 8px;'>
                                <span style='
                                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; 
                                    padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;
                                    box-shadow: 0 2px 4px rgba(40,167,69,0.2);
                                '>
                                    <i class='fa fa-server' style='margin-right: 4px;'></i>
                                    {len(all_configs)} models
                                </span>
                                <span style='
                                    background: linear-gradient(135deg, #007bff 0%, #6610f2 100%); color: white; 
                                    padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;
                                    box-shadow: 0 2px 4px rgba(0,123,255,0.2);
                                '>
                                    <i class='fa fa-list' style='margin-right: 4px;'></i>
                                    {total_fields} total fields
                                </span>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Model Cards Container -->
                    <div style='
                        overflow-x: auto; overflow-y: hidden; white-space: nowrap; 
                        padding: 16px; width: 100%; box-sizing: border-box; 
                        border: 1px solid #dee2e6; border-radius: 12px; 
                        background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%); 
                        margin: 0; position: relative;
                        box-shadow: inset 0 1px 3px rgba(0,0,0,0.04);
                    '>
                        <div style='display: inline-flex; align-items: stretch; gap: 0;'>
                            {model_blocks_html}
                        </div>
                    </div>
                    
                </div>
                """
                
                record.configuration_summary = summary_html
                
            except (json.JSONDecodeError, Exception):
                record.configuration_summary = "<p class='text-danger'><i class='fa fa-exclamation-triangle'></i> Error loading configuration.</p>"

    def execute(self):
        """Override execute to save field selections with ordering"""
        # Always save field configuration if a model is selected (even if no fields selected)
        if self.selected_model:
            try:
                # Get existing configurations
                all_configs = json.loads(self.all_field_configurations or '{}')
                
                if self.selected_signup_field_ids:
                    # Get selected field names IN ORDER (preserve the order from many2many selection)
                    # The order in the many2many field reflects the selection order in the UI
                    field_names = [field.name for field in self.selected_signup_field_ids]
                    # Update configuration for this model with ordered list
                    all_configs[self.selected_model] = field_names
                else:
                    # No fields selected - remove the model from configuration
                    if self.selected_model in all_configs:
                        del all_configs[self.selected_model]
                
                # Save back to parameter
                updated_config = json.dumps(all_configs)
                self.all_field_configurations = updated_config
                self.env['ir.config_parameter'].sudo().set_param(
                    'auth_signup_email_verification.all_field_configurations',
                    updated_config
                )
                
                # Clear the temporary selections
                self.selected_field_ids_json = '[]'
                
            except Exception as e:
                pass  # Silent handling
        
        # Call parent execute
        return super().execute()

    def action_remove_model_config(self):
        """Remove a model configuration immediately"""
        if not self.selected_model:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Warning',
                    'message': 'Please select a model first.',
                    'type': 'warning',
                }
            }
        
        try:
            # Get model name to remove before clearing selection
            model_to_remove = self.selected_model
            
            # Get current configurations from parameter directly
            current_config = self.env['ir.config_parameter'].sudo().get_param(
                'auth_signup_email_verification.all_field_configurations', '{}'
            )
            all_configs = json.loads(current_config)
            
            if model_to_remove in all_configs:
                # Remove the model configuration
                del all_configs[model_to_remove]
                
                # Save updated configuration back to parameter
                updated_config = json.dumps(all_configs)
                self.env['ir.config_parameter'].sudo().set_param(
                    'auth_signup_email_verification.all_field_configurations',
                    updated_config
                )
                
                # Update the current record to reflect changes
                self.all_field_configurations = updated_config
                self.selected_model = False
                self.selected_field_ids_json = '[]'
                
                # Force computation of configuration summary to refresh immediately
                self._compute_configuration_summary()
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': f'Configuration for "{model_to_remove}" removed successfully!',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Warning',
                        'message': f'No configuration found for "{model_to_remove}".',
                        'type': 'warning',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Error removing configuration: {str(e)}',
                    'type': 'danger',
                }
            }
    
    @api.model
    def get_selected_company_fields(self):
        """Get selected fields for company signup - format expected by controller with preserved ordering"""
        try:
            all_configs = self.env['ir.config_parameter'].sudo().get_param(
                'auth_signup_email_verification.all_field_configurations', '{}'
            )
            
            config = json.loads(all_configs) if all_configs else {}
            
            # Convert to format expected by controller - list of field info objects
            fields_list = []
            for model_name, field_names in config.items():
                # Get field details for each field
                model_fields = self.get_model_fields(model_name)
                
                # Create a lookup dictionary for faster access
                fields_dict = {field_info['name']: field_info for field_info in model_fields}
                
                # Add selected fields in the SAME ORDER as configured in settings
                for field_name in field_names:  # This preserves the order!
                    if field_name in fields_dict:
                        field_info = fields_dict[field_name].copy()  # Copy to avoid modifying original
                        # Add model information to field info
                        field_info['source_model'] = model_name
                        fields_list.append(field_info)
            
            return fields_list
        except (json.JSONDecodeError, TypeError, Exception) as e:
            return []
    
    @api.model
    def get_model_fields(self, model_name):
        """Get available fields for a specific model"""
        try:
            model = self.env[model_name]
            fields_list = []
            
            for field_name, field in model._fields.items():
                # Skip technical fields
                if field_name.startswith('_') or \
                   field_name in ['id', 'create_date', 'write_date', 'create_uid', 'write_uid']:
                    continue
                
                # Skip computed fields unless stored
                if getattr(field, 'compute', None) and not getattr(field, 'store', False):
                    continue
                
                field_type = field.type
                
                # Get field string (description)
                field_string = field.get_description(self.env)['string']
                
                # Include comprehensive field types for dynamic signup
                allowed_types = [
                    'char', 'text', 'html', 'selection', 'boolean', 
                    'integer', 'float', 'monetary', 'date', 'datetime',
                    'many2one', 'one2many', 'many2many', 'binary', 'image'
                ]
                if field_type in allowed_types:
                    field_info = {
                        'name': field_name,
                        'string': field_string,
                        'type': field_type,
                        'required': getattr(field, 'required', False),
                    }
                    
                    # Add selection values for selection fields
                    if field_type == 'selection' and hasattr(field, 'selection'):
                        try:
                            selection = field.selection
                            if callable(selection):
                                selection = selection(model)
                            field_info['selection'] = selection
                        except Exception:
                            continue
                    
                    # Add relation options for many2one fields
                    elif field_type == 'many2one' and hasattr(field, 'comodel_name'):
                        try:
                            relation_model_name = field.comodel_name
                            field_info['relation_model'] = relation_model_name
                            
                            try:
                                relation_model = self.env[relation_model_name].sudo()  # Use sudo for access
                                
                                # Get the best field for ordering (must be stored in database)
                                order_field = 'id'  # Safe fallback - always exists and stored
                                
                                # Try to find a better ordering field (stored only)
                                for potential_field in ['name', 'title', 'code', 'sequence']:
                                    if potential_field in relation_model._fields:
                                        field_def = relation_model._fields[potential_field]
                                        # Only use if field is stored (not computed or function field)
                                        if getattr(field_def, 'store', True) and not getattr(field_def, 'compute', None):
                                            order_field = potential_field
                                            break
                                
                                # Build search domain - handle active field if it exists
                                domain = []
                                if 'active' in relation_model._fields:
                                    domain.append(('active', '=', True))
                                
                                # Search with safe ordering - NO LIMIT for complete list
                                try:
                                    records = relation_model.search(domain, order=f'{order_field} asc')
                                except Exception:
                                    # If ordering fails, search without order
                                    records = relation_model.search(domain)
                                
                                # Build relation options (consistent format)
                                relation_options = []
                                for record in records:
                                    # Get the best display value
                                    display_value = str(record.id)  # Safe fallback
                                    
                                    # Try different display options in order of preference
                                    for display_attr in ['display_name', 'name', 'title', 'code']:
                                        try:
                                            if hasattr(record, display_attr):
                                                value = getattr(record, display_attr, None)
                                                if value:
                                                    display_value = str(value)
                                                    break
                                        except Exception:
                                            continue
                                    
                                    # Use tuple format for many2one (backwards compatibility)
                                    relation_options.append((record.id, display_value))
                                
                                field_info['relation_options'] = relation_options
                                
                                # Detect common field dependencies
                                dependency_map = {
                                    'state_id': 'country_id',  # States depend on country
                                    'city_id': 'state_id',     # Cities depend on state  
                                    'district_id': 'city_id',  # Districts depend on city
                                }
                                
                                if field_name in dependency_map:
                                    field_info['depends_on'] = dependency_map[field_name]
                                    field_info['depends_field'] = dependency_map[field_name]
                                
                                # Also check for automatic dependency detection
                                # Look for fields that might be parent fields
                                if relation_model_name == 'res.country.state':
                                    # State fields typically depend on country
                                    field_info['depends_on'] = 'country_id'
                                    field_info['depends_field'] = 'country_id'
                                elif relation_model_name == 'res.city' or 'city' in relation_model_name:
                                    # City fields might depend on state or country
                                    if 'state_id' in model._fields:
                                        field_info['depends_on'] = 'state_id'
                                        field_info['depends_field'] = 'state_id'
                                    elif 'country_id' in model._fields:
                                        field_info['depends_on'] = 'country_id'
                                        field_info['depends_field'] = 'country_id'
                                
                            except Exception:
                                # If we can't load options, still include the field but without options
                                field_info['relation_options'] = []
                        except Exception:
                            # Skip field only if we can't even get the relation model name
                            continue
                    
                    # Add relation options for many2many fields (like Tags)
                    elif field_type == 'many2many' and hasattr(field, 'comodel_name'):
                        try:
                            relation_model_name = field.comodel_name
                            field_info['relation_model'] = relation_model_name
                            field_info['relation_type'] = field_type
                            
                            try:
                                relation_model = self.env[relation_model_name].sudo()  # Use sudo for access
                                
                                # Get the best field for ordering (must be stored in database)
                                order_field = 'id'  # Safe fallback - always exists and stored
                                
                                # Try to find a better ordering field (stored only)
                                for potential_field in ['name', 'title', 'code', 'sequence']:
                                    if potential_field in relation_model._fields:
                                        field_def = relation_model._fields[potential_field]
                                        # Only use if field is stored (not computed or function field)
                                        if getattr(field_def, 'store', True) and not getattr(field_def, 'compute', None):
                                            order_field = potential_field
                                            break
                                
                                # Build search domain - handle active field if it exists
                                domain = []
                                if 'active' in relation_model._fields:
                                    domain.append(('active', '=', True))
                                
                                # Search with safe ordering - NO LIMIT for complete list
                                try:
                                    records = relation_model.search(domain, order=f'{order_field} asc')
                                except Exception:
                                    # If ordering fails, search without order
                                    records = relation_model.search(domain)
                                
                                # Build relation options for many2many with color support
                                relation_options = []
                                for record in records:
                                    # Use display_name for display if available, otherwise use name_field
                                    if hasattr(record, 'display_name'):
                                        display_value = record.display_name
                                    else:
                                        display_value = getattr(record, order_field, str(record.id))
                                    
                                    # Include color information if available
                                    option_data = {
                                        'id': record.id,
                                        'name': display_value,
                                    }
                                    
                                    # Check for color field (common in Odoo models)
                                    if hasattr(record, 'color') and record.color:
                                        option_data['color'] = record.color
                                    
                                    # Check for other color-related fields
                                    for color_field in ['color_name', 'hex_color', 'bg_color']:
                                        if hasattr(record, color_field):
                                            color_value = getattr(record, color_field, None)
                                            if color_value:
                                                option_data[color_field] = color_value
                                    
                                    relation_options.append(option_data)
                                
                                field_info['relation_options'] = relation_options
                                
                                # Add widget information for many2many fields
                                field_info['widget'] = 'many2many_tags'
                                field_info['widget_options'] = {
                                    'no_create': True,  # Don't allow creating new tags from signup
                                    'no_edit': True,    # Don't allow editing tags
                                }
                                
                            except Exception:
                                # If we can't load options, still include the field but without options
                                field_info['relation_options'] = []
                                field_info['widget'] = 'many2many_tags'  # Still add widget info
                        except Exception:
                            # Skip field only if we can't even get the relation model name
                            continue
                    
                    # Handle one2many fields (display-only, no input)
                    elif field_type == 'one2many' and hasattr(field, 'comodel_name'):
                        try:
                            field_info['relation_model'] = field.comodel_name
                            field_info['relation_type'] = field_type
                            field_info['readonly'] = True  # one2many is display only
                        except Exception:
                            continue
                    
                    # Handle binary and image fields
                    elif field_type in ['binary', 'image']:
                        field_info['is_file'] = True
                        field_info['accept'] = 'image/*' if field_type == 'image' else '*/*'
                    
                    # Handle monetary fields
                    elif field_type == 'monetary':
                        field_info['currency_field'] = getattr(field, 'currency_field', 'currency_id')
                    
                    fields_list.append(field_info)
            
            return sorted(fields_list, key=lambda x: x['string'])
        except Exception:
            return []