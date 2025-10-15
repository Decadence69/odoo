/** static/src/js/banner.js **/
odoo.define('website_banner.banner', [], function (require) {
  "use strict";

  // Helper function to decode HTML entities
  function decodeHtml(html) {
    var txt = document.createElement("textarea");
    txt.innerHTML = html;
    return txt.value;
  }

  $(function () {
    $.ajax({
      url: '/home/banner',
      type: 'GET',
      dataType: 'json',
      success: function(result) {
        console.log('Raw result:', result);
        
        let html = result.html || '';
        const bgImage = result.bg_image || '';
        const bgColor = result.bg_color || '';
        
        // Decode HTML entities
        html = decodeHtml(html);
        console.log('Decoded HTML:', html);

        if (!html) return;

        // Remove existing banner if present
        const existingBanner = document.getElementById('mb-banner');
        if (existingBanner) {
          existingBanner.remove();
        }

        // Insert banner after header
        let insertPoint = $('#wrapwrap > header').first();
        
        if (insertPoint.length) {
          insertPoint.after('<div id="mb-banner"></div>');
        } else {
          $('#wrapwrap').prepend('<div id="mb-banner"></div>');
        }

        const el = document.getElementById('mb-banner');
        if (el) {
          // Set innerHTML directly with decoded HTML
          el.innerHTML = html;
          
          // Apply background styling
          if (bgImage) {
            el.style.backgroundImage = `url(data:image/png;base64,${bgImage})`;
            el.style.backgroundSize = 'cover';
            el.style.backgroundPosition = 'center';
            el.style.backgroundRepeat = 'no-repeat';
          } else if (bgColor) {
            el.style.background = bgColor;
          }
          
          // Default banner styles for inline layout
          el.style.padding = '10px 20px';
          el.style.textAlign = 'center';
          el.style.display = 'flex';
          el.style.alignItems = 'center';
          el.style.justifyContent = 'center';
          el.style.gap = '15px';
          el.style.flexWrap = 'wrap';
          el.style.width = '100%';
        }
      },
      error: function(xhr, status, error) {
        console.error('Banner loading error:', status, error);
      }
    });
  });
});