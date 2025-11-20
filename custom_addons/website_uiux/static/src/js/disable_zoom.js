/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.WebsiteSaleDisableZoom = publicWidget.Widget.extend({
    selector: '.o_wsale_product_page',
    
    start: function () {
        // Disable zoom functionality
        this.$el.attr('data-ecom-zoom-auto', '0');
        this.$el.attr('data-ecom-zoom-click', '0');
        this.$el.removeClass('ecom-zoomable');
        this.$el.removeClass('zoomodoo-next');
        
        // Remove zoom attributes from images
        this.$el.find('img[data-zoom]').removeAttr('data-zoom');
        this.$el.find('img[data-zoom-image]').removeAttr('data-zoom-image');
        
        return this._super.apply(this, arguments);
    },
});

export default publicWidget.registry.WebsiteSaleDisableZoom;