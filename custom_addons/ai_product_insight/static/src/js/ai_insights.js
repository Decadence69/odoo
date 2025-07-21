/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";

console.log('Loading AI Insights module...');

// AI Insights Widget
const AIInsightsWidget = publicWidget.Widget.extend({
    selector: '.ai-insights-btn',
    events: {
        'click': '_onClickInsights',
    },
    
    /**
     * Initialize the widget
     */
    start: function () {
        console.log('AIInsightsWidget started for element:', this.$el);
        return this._super.apply(this, arguments);
    },
    
    /**
     * Handle click on AI Insights button
     */
    _onClickInsights: function (ev) {
        console.log('Button clicked!', ev);
        ev.preventDefault();
        ev.stopPropagation();
        ev.stopImmediatePropagation();
        
        var $btn = $(ev.currentTarget);
        var productId = $btn.data('product-id');
        
        console.log('Product ID:', productId);
        
        if (!productId) {
            console.error('Product ID not found');
            return false;
        }
        
        this._showInsightsModal(productId);
        return false;
    },
    
    /**
     * Show the AI insights modal
     */
    _showInsightsModal: function (productId) {
        console.log('Showing modal for product:', productId);
        var self = this;
        
        // Create modal if it doesn't exist
        if (!$('#aiInsightsModal').length) {
            this._createModal();
        }
        
        var $modal = $('#aiInsightsModal');
        
        // Show modal
        $modal.modal('show');
        
        // Load insights
        this._loadInsights(productId);
        
        // Bind events
        $modal.find('#generate-insights-btn').off('click').on('click', function() {
            self._generateInsights(productId);
        });
        
        $modal.find('#refresh-insights-btn').off('click').on('click', function() {
            self._generateInsights(productId);
        });
    },
    
    /**
     * Create the modal HTML
     */
    _createModal: function () {
        console.log('Creating modal...');
        var modalHtml = `
            <div class="modal fade" id="aiInsightsModal" tabindex="-1" role="dialog" aria-labelledby="aiInsightsModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="aiInsightsModalLabel">
                                <i class="fa fa-brain mr-2"></i>
                                AI Insights for <span></span>
                            </h5>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close">
                                <span aria-hidden="true">&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <div id="insights-loading" class="text-center" style="display: none;">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="sr-only">Loading...</span>
                                </div>
                                <p class="mt-2">Loading AI insights...</p>
                            </div>
                            
                            <div id="insights-content"></div>
                            
                            <div id="insights-error" class="alert alert-danger" style="display: none;">
                                <i class="fa fa-exclamation-triangle mr-2"></i>
                                <span id="error-message">An error occurred while loading insights.</span>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" id="refresh-insights-btn">
                                <i class="fa fa-refresh mr-2"></i> Refresh Insights
                            </button>
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(modalHtml);
    },
    
    /**
     * Load existing insights for a product
     */
    _loadInsights: function (productId) {
        console.log('Loading insights for product:', productId);
        var self = this;
        
        this._showLoading();
        
        // Updated RPC call for Odoo 18
        rpc('/ai_insights/get', {
            product_id: productId,
        }).then((result) => {
            console.log('Raw RPC response:', result);
            console.log('Response type:', typeof result);
            console.log('Response keys:', result ? Object.keys(result) : 'null/undefined');
            
            self._hideLoading();
            
            // Handle different response formats
            if (result && typeof result === 'object') {
                if (result.success && result.data) {
                    self._displayInsights(result);
                } else if (result.success === false) {
                    self._showError(result.error || 'Unknown error occurred');
                } else if (result.data) {
                    // Handle case where success property might be missing but data exists
                    self._displayInsights({success: true, data: result.data, last_updated: result.last_updated});
                } else {
                    self._showNoInsights();
                }
            } else {
                console.error('Unexpected response format:', result);
                self._showNoInsights();
            }
        }).catch(function (error) {
            console.error('Error loading insights:', error);
            console.error('Error details:', error.data);
            self._hideLoading();
            self._showError('Failed to load insights: ' + (error.message || error.toString()));
        });
    },
    
    /**
     * Generate new insights for a product
     */
    _generateInsights: function (productId) {
        console.log('Generating insights for product:', productId);
        var self = this;
        
        this._showLoading('Generating AI insights...');
        
        // Updated RPC call for Odoo 18
        rpc('/ai_insights/generate', {
            product_id: productId
        }).then((result) => {
            console.log('Raw generation response:', result);
            console.log('Response type:', typeof result);
            console.log('Response keys:', result ? Object.keys(result) : 'null/undefined');
            
            self._hideLoading();
            
            // Handle different response formats
            if (result && typeof result === 'object') {
                if (result.success && result.data) {
                    self._displayInsights(result);
                } else if (result.success === false) {
                    self._showError(result.error || 'Failed to generate insights');
                } else if (result.data) {
                    // Handle case where success property might be missing but data exists
                    self._displayInsights({success: true, data: result.data, last_updated: result.last_updated});
                } else {
                    self._showError('Failed to generate insights - no data returned');
                }
            } else {
                console.error('Unexpected response format:', result);
                self._showError('Unexpected response format from server');
            }
        }).catch(function (error) {
            console.error('Error generating insights:', error);
            console.error('Error details:', error.data);
            self._hideLoading();
            self._showError('Failed to generate insights: ' + (error.message || error.toString()));
        });
    },
    
    /**
     * Display insights in the modal
     */
    _displayInsights: function (insights) {
        var $content = $('#insights-content');
        var data = insights.data || {};
        
        var html = '';
        
        // Key Features
        if (data.key_features && data.key_features.length) {
            html += '<div class="mb-4">';
            html += '<h6 class="text-primary"><i class="fa fa-star me-2"></i>Key Features</h6>';
            html += '<ul class="list-unstyled">';
            data.key_features.forEach(function(feature) {
                html += '<li><i class="fa fa-check text-success me-2"></i>' + feature + '</li>';
            });
            html += '</ul></div>';
        }
        
        // Target Audience
        if (data.target_audience) {
            html += '<div class="mb-4">';
            html += '<h6 class="text-primary"><i class="fa fa-users me-2"></i>Target Audience</h6>';
            html += '<p>' + data.target_audience + '</p>';
            html += '</div>';
        }
        
        // Use Cases
        if (data.use_cases && data.use_cases.length) {
            html += '<div class="mb-4">';
            html += '<h6 class="text-primary"><i class="fa fa-lightbulb me-2"></i>Use Cases</h6>';
            html += '<ul class="list-unstyled">';
            data.use_cases.forEach(function(useCase) {
                html += '<li><i class="fa fa-arrow-right text-info me-2"></i>' + useCase + '</li>';
            });
            html += '</ul></div>';
        }
        
        // Competitive Advantages
        if (data.competitive_advantages && data.competitive_advantages.length) {
            html += '<div class="mb-4">';
            html += '<h6 class="text-primary"><i class="fa fa-trophy me-2"></i>Competitive Advantages</h6>';
            html += '<ul class="list-unstyled">';
            data.competitive_advantages.forEach(function(advantage) {
                html += '<li><i class="fa fa-plus text-success me-2"></i>' + advantage + '</li>';
            });
            html += '</ul></div>';
        }
        
        // Recommendations
        if (data.recommendations && data.recommendations.length) {
            html += '<div class="mb-4">';
            html += '<h6 class="text-primary"><i class="fa fa-compass me-2"></i>Recommendations</h6>';
            html += '<ul class="list-unstyled">';
            data.recommendations.forEach(function(rec) {
                html += '<li><i class="fa fa-thumbs-up text-warning me-2"></i>' + rec + '</li>';
            });
            html += '</ul></div>';
        }
        
        // Marketing Angles
        if (data.marketing_angles && data.marketing_angles.length) {
            html += '<div class="mb-4">';
            html += '<h6 class="text-primary"><i class="fa fa-megaphone me-2"></i>Marketing Angles</h6>';
            html += '<ul class="list-unstyled">';
            data.marketing_angles.forEach(function(angle) {
                html += '<li><i class="fa fa-bullhorn text-primary me-2"></i>' + angle + '</li>';
            });
            html += '</ul></div>';
        }
        
        // Raw text fallback
        if (data.raw_text) {
            html += '<div class="mb-4">';
            html += '<h6 class="text-primary"><i class="fa fa-info-circle me-2"></i>AI Analysis</h6>';
            html += '<p>' + data.raw_text + '</p>';
            html += '</div>';
        }
        
        // Last updated
        if (insights.last_updated) {
            html += '<div class="text-muted small">';
            html += '<i class="fa fa-clock me-1"></i>Last updated: ' + insights.last_updated;
            html += '</div>';
        }
        
        // Default message if no content
        if (!html) {
            html = '<div class="text-center"><p>AI Insights will be displayed here.</p></div>';
        }
        
        $content.html(html);
    },
    
    /**
     * Show no insights message
     */
    _showNoInsights: function () {
        var html = `
            <div class="text-center">
                <i class="fa fa-info-circle fa-3x text-muted mb-3"></i>
                <p>No AI insights available yet. Click "Generate Insights" to create them.</p>
                <button class="btn btn-primary" id="generate-insights-btn">
                    <i class="fa fa-cog me-2"></i>Generate Insights
                </button>
            </div>
        `;
        
        $('#insights-content').html(html);
    },
    
    /**
     * Show loading state
     */
    _showLoading: function (message) {
        message = message || 'Loading AI insights...';
        $('#insights-loading p').text(message);
        $('#insights-loading').show();
        $('#insights-content').hide();
        $('#insights-error').hide();
    },
    
    /**
     * Hide loading state
     */
    _hideLoading: function () {
        $('#insights-loading').hide();
        $('#insights-content').show();
    },
    
    /**
     * Show error message
     */
    _showError: function (message) {
        $('#error-message').text(message);
        $('#insights-error').show();
        $('#insights-content').hide();
    }
});

console.log('Registering AIInsightsWidget...');
publicWidget.registry.AIInsightsWidget = AIInsightsWidget;

console.log('AI Insights module defined successfully');
export default AIInsightsWidget;