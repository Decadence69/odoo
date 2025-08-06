odoo.define('dental_ai_assistant.widget', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');
    var Dialog = require('web.Dialog');

    var _t = core._t;

    // Add global function for the button onclick
    window.getAIRecommendation = function() {
        var query = document.querySelector('input[name="query"]').value;
        
        if (!query.trim()) {
            alert('Please enter a question about dental procedures or tools.');
            return;
        }

        // Show loading
        document.getElementById('ai-loading').style.display = 'block';
        document.getElementById('ai-response').style.display = 'none';

        rpc.query({
            route: '/api/dental-ai/recommend',
            params: {
                query: query
            }
        }).then(function(result) {
            document.getElementById('ai-loading').style.display = 'none';
            
            if (result.success) {
                document.getElementById('ai-recommendation-content').innerHTML = result.recommendation;
                document.getElementById('ai-sources').textContent = result.sources.join(', ');
                document.getElementById('ai-response').style.display = 'block';
            } else {
                alert('Error: ' + (result.error || 'Unknown error occurred'));
            }
        }).catch(function(error) {
            document.getElementById('ai-loading').style.display = 'none';
            console.error('API Error:', error);
            alert('Failed to get AI recommendation. Please try again.');
        });
    };

    var DentalAIWidget = Widget.extend({
        template: 'DentalAIAssistant',
        
        events: {
            'click .get-recommendation-btn': '_onGetRecommendation',
            'keypress .query-input': '_onQueryKeypress',
        },

        _onQueryKeypress: function(ev) {
            if (ev.which === 13) { // Enter key
                this._onGetRecommendation();
            }
        },

        _onGetRecommendation: function(ev) {
            ev.preventDefault();
            var query = this.$('.query-input').val().trim();
            
            if (!query) {
                this.displayNotification({
                    type: 'warning',
                    title: _t('Warning'),
                    message: _t('Please enter a question about dental procedures or tools.')
                });
                return;
            }

            this._showLoading(true);
            
            rpc.query({
                route: '/api/dental-ai/recommend',
                params: { query: query }
            }).then(function(result) {
                this._showLoading(false);
                
                if (result.success) {
                    this._displayRecommendation(result);
                } else {
                    this._showError(result.error || 'Unknown error occurred');
                }
            }.bind(this)).catch(function(error) {
                this._showLoading(false);
                this._showError('Failed to get AI recommendation. Please try again.');
                console.error('API Error:', error);
            }.bind(this));
        },

        _showLoading: function(show) {
            this.$('.ai-loading').toggle(show);
            this.$('.ai-response').toggle(!show && false); // Hide response during loading
            this.$('.get-recommendation-btn').prop('disabled', show);
        },

        _displayRecommendation: function(result) {
            this.$('.ai-recommendation-content').html(result.recommendation);
            this.$('.ai-sources').text(result.sources.join(', '));
            this.$('.ai-response').show();
        },

        _showError: function(message) {
            this.displayNotification({
                type: 'danger',
                title: _t('Error'),
                message: message
            });
        }
    });

    return DentalAIWidget;
});