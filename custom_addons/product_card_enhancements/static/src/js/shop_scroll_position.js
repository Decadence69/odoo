/** @odoo-module **/

// Scroll position manager for Odoo shop
(function() {
    'use strict';

    function init() {
        const isShopPage = window.location.pathname.includes('/shop');
        const isProductPage = window.location.pathname.includes('/shop/');

        // On product page: Intercept breadcrumb to use history.back()
        if (isProductPage) {
            attachBackNavigation();
            
            // Also watch for dynamically added breadcrumbs
            const observer = new MutationObserver(() => {
                attachBackNavigation();
            });
            
            const breadcrumb = document.querySelector('.breadcrumb');
            if (breadcrumb) {
                observer.observe(breadcrumb, { childList: true, subtree: true });
            }
        }

        // On shop page: Also intercept if someone clicks "All Products" after browsing
        if (isShopPage) {
            const fromProduct = document.referrer.includes('/shop/product/');
        }
    }

    function attachBackNavigation() {
        const breadcrumbLinks = document.querySelectorAll('.breadcrumb a');
        
        let attached = 0;
        breadcrumbLinks.forEach((link, index) => {
            // Skip if already has our listener
            if (link.hasAttribute('data-back-nav-attached')) {
                return;
            }
            
            const href = link.getAttribute('href') || '';
            const text = link.textContent.trim();
            
            
            // Intercept any link that goes to /shop (but not product pages)
            if (href && !href.includes('/product/') && 
                (href === '/shop' || href.includes('/shop?') || href.match(/\/shop\/?$/))) {
                
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    window.history.back();
                });
                
                // Mark as processed
                link.setAttribute('data-back-nav-attached', 'true');
                attached++;
            }
        });
    }

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            // Add small delay to ensure Odoo has finished rendering
            setTimeout(init, 100);
        });
    } else {
        // DOM is already ready, but wait a bit for Odoo rendering
        setTimeout(init, 100);
    }

})();