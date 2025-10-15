import logging
import os
import requests
import tarfile
import shutil
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class GeoDbUpdater(models.Model):
    _name = 'geo.db.updater'
    _description = 'GeoLite2 Database Updater'
    
    name = fields.Char(string='Update Name', compute='_compute_name', store=True)
    last_update = fields.Datetime(string='Last Update', readonly=True)
    next_update = fields.Datetime(string='Next Update', readonly=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed')
    ], string='Status', default='pending', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    db_path = fields.Char(
        string='Database Path',
        default='C:/geoip/GeoLite2-Country.mmdb',
        help='Full path where the GeoLite2 database file is stored'
    )
    license_key = fields.Char(
        string='MaxMind License Key',
        help='Your MaxMind license key for downloading GeoLite2 database. Get one free at https://www.maxmind.com/en/geolite2/signup'
    )
    
    @api.depends('last_update')
    def _compute_name(self):
        for record in self:
            if record.last_update:
                record.name = f"GeoLite2 Update - {record.last_update.strftime('%Y-%m-%d %H:%M')}"
            else:
                record.name = "GeoLite2 Update - Never"
    
    def _download_database(self):
        """Download the latest GeoLite2 database from MaxMind"""
        self.ensure_one()
        
        if not self.license_key:
            raise UserError('MaxMind license key is required. Please configure it in the settings.')
        
        # MaxMind download URL for GeoLite2 Country database
        edition_id = 'GeoLite2-Country'
        suffix = 'tar.gz'
        download_url = f'https://download.maxmind.com/app/geoip_download?edition_id={edition_id}&license_key={self.license_key}&suffix={suffix}'
        
        _logger.info('Downloading GeoLite2 database...')
        
        try:
            # Download the tar.gz file
            response = requests.get(download_url, timeout=300)  # 5 minute timeout
            response.raise_for_status()
            
            # Create temporary directory
            temp_dir = '/tmp/geoip_temp'
            os.makedirs(temp_dir, exist_ok=True)
            
            # Save tar.gz file
            tar_path = os.path.join(temp_dir, 'GeoLite2-Country.tar.gz')
            with open(tar_path, 'wb') as f:
                f.write(response.content)
            
            _logger.info(f'Downloaded {len(response.content)} bytes')
            return tar_path, temp_dir
            
        except requests.exceptions.RequestException as e:
            raise UserError(f'Failed to download database: {str(e)}')
    
    def _extract_database(self, tar_path, temp_dir):
        """Extract the .mmdb file from the downloaded tar.gz"""
        self.ensure_one()
        
        _logger.info('Extracting database...')
        
        try:
            # Extract tar.gz
            with tarfile.open(tar_path, 'r:gz') as tar:
                tar.extractall(path=temp_dir)
            
            # Find the .mmdb file (it's inside a dated directory)
            mmdb_file = None
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith('.mmdb'):
                        mmdb_file = os.path.join(root, file)
                        break
                if mmdb_file:
                    break
            
            if not mmdb_file:
                raise UserError('Could not find .mmdb file in downloaded archive')
            
            _logger.info(f'Found database file: {mmdb_file}')
            return mmdb_file
            
        except Exception as e:
            raise UserError(f'Failed to extract database: {str(e)}')
    
    def _install_database(self, source_path):
        """Install the new database file to the configured location"""
        self.ensure_one()
        
        _logger.info(f'Installing database to {self.db_path}...')
        
        try:
            # Create directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            os.makedirs(db_dir, exist_ok=True)
            
            # Backup existing database if it exists
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.backup"
                shutil.copy2(self.db_path, backup_path)
                _logger.info(f'Backed up existing database to {backup_path}')
            
            # Copy new database
            shutil.copy2(source_path, self.db_path)
            _logger.info('Database installed successfully')
            
        except Exception as e:
            raise UserError(f'Failed to install database: {str(e)}')
    
    def update_database(self):
        """Main method to update the GeoLite2 database"""
        self.ensure_one()
        
        self.write({'status': 'running'})
        
        temp_dir = None
        try:
            # Download database
            tar_path, temp_dir = self._download_database()
            
            # Extract database
            mmdb_file = self._extract_database(tar_path, temp_dir)
            
            # Install database
            self._install_database(mmdb_file)
            
            # Update status
            self.write({
                'status': 'success',
                'last_update': fields.Datetime.now(),
                'next_update': fields.Datetime.add(fields.Datetime.now(), months=2),
                'error_message': False
            })
            
            _logger.info('GeoLite2 database updated successfully')
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f'Failed to update GeoLite2 database: {error_msg}')
            self.write({
                'status': 'failed',
                'error_message': error_msg
            })
            raise
            
        finally:
            # Cleanup temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    _logger.info('Cleaned up temporary files')
                except Exception as e:
                    _logger.warning(f'Failed to cleanup temp directory: {str(e)}')
    
    @api.model
    def cron_update_database(self):
        """Cron job method to update the database"""
        _logger.info('Running GeoLite2 database update cron job...')
        
        # Get or create the updater record
        updater = self.search([], limit=1)
        if not updater:
            updater = self.create({
                'status': 'pending'
            })
        
        # Check if license key is configured
        if not updater.license_key:
            _logger.warning('MaxMind license key not configured. Skipping database update.')
            return
        
        # Check if update is needed
        if updater.next_update and updater.next_update > fields.Datetime.now():
            _logger.info(f'Next update scheduled for {updater.next_update}. Skipping.')
            return
        
        # Perform update
        updater.update_database()
    
    def action_manual_update(self):
        """Manual update action for the button"""
        self.ensure_one()
        self.update_database()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'GeoLite2 database updated successfully',
                'type': 'success',
                'sticky': False,
            }
        }