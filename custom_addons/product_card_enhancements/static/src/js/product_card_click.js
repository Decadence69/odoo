/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ProductCardClickable = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    
    start: function () {
        this._makeProductCardsClickable();
        return this._super.apply(this, arguments);
    },
    
    _makeProductCardsClickable: function () {
        const productForms = document.querySelectorAll('form[action^="/shop/cart/update"]');
        
        console.log('Product card click script loaded - Found ' + productForms.length + ' product cards');
        
        productForms.forEach(function(form) {
            const link = form.querySelector('.o_wsale_products_item_title a[href^="/shop/"]');
            
            if (link) {
                form.style.cursor = 'pointer';
                
                form.addEventListener('click', function(e) {
                    if (!e.target.closest('button, .btn, input, a, select, textarea')) {
                        e.preventDefault();
                        window.location.href = link.href;
                    }
                });
            }
        });
    },
});

export default publicWidget.registry.ProductCardClickable;