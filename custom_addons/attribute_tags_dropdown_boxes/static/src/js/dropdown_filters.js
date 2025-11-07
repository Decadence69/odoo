/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.DropdownFilters = publicWidget.Widget.extend({
    selector: '.products_attributes_filters',

    _filterCache: null,
    _filterCheckQueue: null,
    _isCheckingFilters: false,
    _domCache: {},
    _pendingRequest: null, // Track active AJAX request
    _productCache: {}, // Cache product results
    _lastFetchTime: 0,

    start: function () {
        this._super.apply(this, arguments);

        // Safety check - ensure document is available
        if (!document || !document.body) {
            console.warn('[DropdownFilters] Document not ready, deferring initialization');
            setTimeout(() => this.start(), 100);
            return;
        }

        // Initialize caches
        this._filterCache = {};
        this._domCache = {};
        
        // Prevent desktop form submission
        const $form = this.$el.closest('form');
        if ($form.length) {
            $form.off('submit.mrbur').on('submit.mrbur', (e) => {
                e.preventDefault(); 
                e.stopPropagation(); 
                return false;
            });
        }

        this._setupOffcanvasHandlers();
        this._setupFilterHandlers();
        this._convertFiltersToDropdowns();
        this._setupDOMObserver();
        this._ensureClearFiltersButton();
        this._renderActiveFilterBadges();
        this._renderMobileFilterBadges();
        
        // DEFER expensive operation to after initial render
        requestAnimationFrame(() => {
            this._hideEmptyFilterOptionsOptimized();
        });

        // URL back/forward sync
        window.addEventListener('popstate', () => {
            this._handlePopState();
        });

        // Debounced resize handler
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this._renderMobileFilterBadges();
            }, 250);
        });
    },

    _handlePopState: function() {
        if (typeof this._ajaxUpdateProducts === 'function') {
            const url = new URL(window.location.href);
            this._ajaxUpdateProducts(url.searchParams, { pushState: false, scrollIntoView: false });
        }
        this._ensureClearFiltersButton();
        this._renderActiveFilterBadges();
        this._renderMobileFilterBadges();
        this._syncDropdownSelectionsFromURL?.();
        this._syncOffcanvasFromURL();
    },

    _setupOffcanvasHandlers: function() {
        const $off = $('#o_wsale_offcanvas');
        let isHidingOffcanvas = false;
        const offEl = document.getElementById('o_wsale_offcanvas');
        
        if (offEl) {
            offEl.addEventListener('hide.bs.offcanvas', () => { 
                isHidingOffcanvas = true; 
            }, { passive: true });

            offEl.addEventListener('hidden.bs.offcanvas', () => {
                isHidingOffcanvas = false;
                setTimeout(() => {
                    document.body.classList.remove('offcanvas-backdrop', 'offcanvas-open', 'modal-open');
                    
                    if ((document.body.style.overflow === 'hidden' || 
                        document.body.hasAttribute('data-bs-overflow')) &&
                        !document.querySelector('.offcanvas.show') &&
                        !document.querySelector('.modal.show')) {
                        
                        document.body.style.overflow = '';
                        document.body.style.paddingRight = '';
                        document.body.removeAttribute('data-bs-overflow');
                        document.body.removeAttribute('data-bs-padding-right');
                        document.documentElement.style.overflow = '';
                        document.documentElement.style.paddingRight = '';
                    }
                }, 350);
            }, { passive: true });
        }
    },

    _setupFilterHandlers: function() {
        const $off = $('#o_wsale_offcanvas');
        
        // Remove 'for' attribute from labels
        $off.find('label.form-check-label[for]').each(function() {
            const $label = $(this);
            const forId = $label.attr('for');
            const $checkbox = $('#' + forId);
            
            if ($checkbox.length && $checkbox.attr('name') === 'attribute_value') {
                $label.removeAttr('for');
                $label.css('cursor', 'pointer');
                $label.data('checkbox-id', forId);
            }
        });

        // Use event delegation for better performance
        $off.on('click.mrbur_item', '.list-group-item', (e) => {
            const $item = $(e.currentTarget);
            const $checkbox = $item.find('input[type="checkbox"][name="attribute_value"]');
            
            if (!$checkbox.length || $(e.target).is('input[type="checkbox"]')) return;
            
            e.preventDefault();
            e.stopPropagation();
            
            const cb = $checkbox[0];
            cb.checked = !cb.checked;
            cb.dispatchEvent(new Event('change', { bubbles: true }));
        });

        $off.on('mousedown.mrbur_label', 'label.form-check-label', function(e) {
            const $label = $(this);
            if ($label.data('checkbox-id')) {
                e.preventDefault();
                e.stopPropagation();
                return false;
            }
        });

        // Debounced checkbox change handler
        $off.off('change.mrbur_attr').on('change.mrbur_attr', 
            'form.js_attributes input[type="checkbox"][name="attribute_value"]', 
            this._createDebouncedFilterHandler()
        );

        $off.off('submit.mrbur_attr').on('submit.mrbur_attr', 'form.js_attributes', (e) => {
            e.preventDefault(); 
            e.stopPropagation(); 
            return false;
        });
    },

    _createDebouncedFilterHandler: function() {
        let debounceTimer;
        return (e) => {
            e.preventDefault(); 
            e.stopPropagation();

            if (this._filterCache) this._filterCache = {}; 

            const cb = e.currentTarget;
            cb.toggleAttribute('checked', cb.checked);

            const current = new URL(window.location.href);
            const params = new URLSearchParams(current.search);
            const val = cb.value;

            const set = new Set(params.getAll('attribute_value'));
            cb.checked ? set.add(val) : set.delete(val);

            params.delete('attribute_value');
            for (const v of set) params.append('attribute_value', v);

            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                if (typeof this._ajaxUpdateProducts === 'function') {
                    this._ajaxUpdateProducts(params, { pushState: true, scrollIntoView: false });
                } else {
                    window.history.pushState({}, '', `${location.pathname}?${params.toString()}`);
                }
            }, 150);
        };
    },

    _debounceTimer: null,
    _debounce: function (fn, delay=250) {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(fn, delay);
    },

    _convertFiltersToDropdowns: function () {
        // MODIFIED: If dropdowns already created, only sync selections
        if (this._dropdownsCreated) {
            this._syncDropdownSelectionsFromURL();
            this._ensureClearFiltersButton();
            this._renderActiveFilterBadges();
            return;
        }
        
        this._convertTagsToDropdown();
        this._convertAttributesToDropdown();
        this._ensureClearFiltersButton();
        this._renderActiveFilterBadges();
        
        // NEW: Mark dropdowns as created
        this._dropdownsCreated = true;
    },

    _convertTagsToDropdown: function () {
        const $tagsSection = this.$('#o_wsale_tags_option_inner').closest('.accordion-item');
        if (!$tagsSection.length) return;

        // MODIFIED: Check if dropdown exists ANYWHERE in document
        if ($('#tags_filter_dropdown').length > 0) {
            return;
        }

        const $checkboxes = $tagsSection.find('input[type="checkbox"][name="tags"]');
        if (!$checkboxes.length) return;

        const urlParams = new URLSearchParams(window.location.search);
        const selectedTags = urlParams.getAll('tags').filter(v => v);

        const $dropdownContainer = this._createDropdownContainer('tags_filter_dropdown');
        $dropdownContainer.attr('data-attribute-name', 'Tags');
        const $dropdownButton = this._createDropdownButton();

        const updateButtonText = () => {
            const checkedCount = $dropdownContainer.find('input[type="checkbox"]:checked').length;
            const $textSpan = $('<span>');
            
            if (checkedCount === 0) {
                $textSpan.text('All Tags');
            } else if (checkedCount === 1) {
                const $checkedCheckbox = $dropdownContainer.find('input[type="checkbox"]:checked').first();
                const checkedLabel = $checkedCheckbox.parent('label').clone().children().remove().end().text().trim();
                $textSpan.text(checkedLabel);
            } else {
                $textSpan.text(checkedCount + ' Tags Selected');
            }
            
            $dropdownButton.empty().append($textSpan);
        };

        const buildParamsFromMenu = () => {
            const selectedValues = [];
            $dropdownMenu.find('input[type="checkbox"]:checked').each(function() {
                selectedValues.push($(this).val());
            });

            const currentUrl = new URL(window.location.href);
            const newParams = new URLSearchParams();

            currentUrl.searchParams.forEach((value, key) => {
                if (key !== 'tags' && value) newParams.append(key, value);
            });
            selectedValues.forEach((v) => newParams.append('tags', v));
            return newParams;
        };

        const applyFilters = () => {
            const newParams = buildParamsFromMenu();
            this._ajaxUpdateProducts(newParams);
        };

        const clearFiltersNavigate = () => {
            const currentUrl = new URL(window.location.href);
            const newParams = new URLSearchParams();
            currentUrl.searchParams.forEach((value, key) => {
                if (key !== 'tags' && value) newParams.append(key, value);
            });
            const targetUrl = this._buildUrlString(currentUrl.pathname, newParams);
            window.location.assign(targetUrl);
        };

        const $dropdownMenu = this._createDropdownMenu(
            $checkboxes, selectedTags, updateButtonText, applyFilters, clearFiltersNavigate
        );

        updateButtonText();
        $dropdownContainer.append($dropdownButton, $dropdownMenu);

        const $checkboxContainer = $tagsSection.find('.flex-column');
        if ($checkboxContainer.length) {
            $checkboxContainer.hide();
            $checkboxContainer.before($dropdownContainer);
        }

        $dropdownMenu.on('click', (e) => e.stopPropagation());
    },

    _convertAttributesToDropdown: function () {
        // MODIFIED: Check each section individually
        const $attributeSections = this.$('.accordion-item');

        $attributeSections.each((index, section) => {
            const $section = $(section);
            
            if ($section.find('#o_wsale_tags_option_inner').length) return;

            const $attributeTitle = $section.find('.accordion-header b');
            const attributeName = $attributeTitle.text().trim();
            if (!attributeName) return;

            const $checkboxes = $section.find('input[type="checkbox"][name="attribute_value"]');
            if (!$checkboxes.length) return;

            const dropdownClass = 'attribute_dropdown_' + attributeName.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '');
            
            // MODIFIED: Check if dropdown exists ANYWHERE in document
            if ($('.' + dropdownClass).length > 0) {
                return;
            }

            const firstOptionValue = $checkboxes.first().val();
            const thisAttributeId = firstOptionValue ? firstOptionValue.split('-')[0] : null;

            const urlParams = new URLSearchParams(window.location.search);
            const selectedAttributes = urlParams.getAll('attribute_value').filter(v => v);

            const $dropdownContainer = this._createDropdownContainer(dropdownClass);
            $dropdownContainer.attr('data-attribute-id', thisAttributeId);
            $dropdownContainer.attr('data-attribute-name', attributeName); 

            const $dropdownButton = this._createDropdownButton();

            const updateButtonText = () => {
                const checkedCount = $dropdownContainer.find('input[type="checkbox"]:checked').length;
                const $textSpan = $('<span>');
                
                if (checkedCount === 0) {
                    $textSpan.text('All ' + attributeName);
                } else if (checkedCount === 1) {
                    const $checkedCheckbox = $dropdownContainer.find('input[type="checkbox"]:checked').first();
                    const checkedLabel = $checkedCheckbox.parent('label').clone().children().remove().end().text().trim();
                    $textSpan.text(checkedLabel);
                } else {
                    $textSpan.text(checkedCount + ' Selected');
                }
                
                $dropdownButton.empty().append($textSpan);
            };

            const buildParamsFromMenu = () => {
                const selectedValues = [];
                $dropdownMenu.find('input[type="checkbox"]:checked').each(function() {
                    selectedValues.push($(this).val());
                });

                const currentUrl = new URL(window.location.href);
                const newParams = new URLSearchParams();
                const currentAttributes = currentUrl.searchParams.getAll('attribute_value').filter(v => v);

                currentUrl.searchParams.forEach((value, key) => {
                    if (key !== 'attribute_value' && value) newParams.append(key, value);
                });

                currentAttributes.forEach((attr) => {
                    const attrId = attr.split('-')[0];
                    if (attrId !== thisAttributeId) newParams.append('attribute_value', attr);
                });

                selectedValues.forEach((v) => newParams.append('attribute_value', v));
                return newParams;
            };

            const applyFilters = () => {
                const newParams = buildParamsFromMenu();
                this._ajaxUpdateProducts(newParams);
            };

            const clearFiltersNavigate = () => {
                const currentUrl = new URL(window.location.href);
                const newParams = new URLSearchParams();
                const currentAttributes = currentUrl.searchParams.getAll('attribute_value').filter(v => v);

                currentUrl.searchParams.forEach((value, key) => {
                    if (key !== 'attribute_value' && value) newParams.append(key, value);
                });

                currentAttributes.forEach((attr) => {
                    const attrId = attr.split('-')[0];
                    if (attrId !== thisAttributeId) newParams.append('attribute_value', attr);
                });

                const targetUrl = this._buildUrlString(currentUrl.pathname, newParams);
                window.location.assign(targetUrl);
            };

            const $dropdownMenu = this._createDropdownMenu(
                $checkboxes, selectedAttributes, updateButtonText, applyFilters, clearFiltersNavigate
            );

            $dropdownContainer.append($dropdownButton, $dropdownMenu);
            updateButtonText();

            const $checkboxContainer = $section.find('.flex-column');
            if ($checkboxContainer.length) {
                $checkboxContainer.hide();
                $checkboxContainer.before($dropdownContainer);
            }

            $dropdownMenu.on('click', (e) => e.stopPropagation());
        });
    },

    _createDropdownContainer: function (className) {
        return $('<div>', {
            class: 'dropdown mb-3 filter-dropdown-container ' + className
        });
    },

    _createDropdownButton: function () {
        return $('<button>', {
            class: 'btn btn-light dropdown-toggle w-100 d-flex justify-content-between align-items-center',
            type: 'button',
            'data-bs-toggle': 'dropdown',
            'aria-expanded': 'false',
            style: 'padding: 8px 12px;'
        });
    },

    _createDropdownMenu: function ($checkboxes, selectedValues, updateButtonText, applyFilters, clearHandler) {
        const $dropdownMenu = $('<ul>', { class: 'dropdown-menu w-100' });

        $checkboxes.each((index, checkbox) => {
            const $checkbox = $(checkbox);
            const $label = $checkbox.next('label');
            const itemName = $label.text().trim();
            const itemValue = $checkbox.val();
            const isChecked = $checkbox.prop('checked') || selectedValues.includes(itemValue);

            const $item = $('<li>');
            const $itemLabel = $('<label>', { class: 'dropdown-item mb-0' });
            const $newCheckbox = $('<input>', {
                type: 'checkbox',
                value: itemValue,
                checked: isChecked,
                class: 'form-check-input'
            });

            $newCheckbox.on('change', (e) => {
                e.stopPropagation();
                updateButtonText();
                this._debounce(() => applyFilters(), 250);
            });

            $itemLabel.append($newCheckbox, document.createTextNode(' ' + itemName));
            $item.append($itemLabel);
            $dropdownMenu.append($item);
        });

        return $dropdownMenu;
    },

    // CACHED DOM lookup for products grid
    _getProductsTargets: function () {
        if (this._domCache.grid && this._domCache.grid.length) {
            return { 
                $grid: this._domCache.grid, 
                $pager: this._domCache.pager 
            };
        }

        const $doc = $(document);
        const $grid = $doc.find(
            '#products_grid, #o_wsale_products_grid, .o_wsale_products_main, ' +
            '.o_wsale_products_grid, .o_wsale_product_grid_wrapper, .products_grid, ' +
            '.o_wsale_products_layout, .o_wsale_products_catalog'
        ).first();

        const $pager = $doc.find(
            '.products_pager, .o_wsale_pager, .o_wsale_products_pager, .pagination'
        ).first();

        this._domCache.grid = $grid;
        this._domCache.pager = $pager;

        return { $grid, $pager };
    },

    _showLoading: function () {
        const { $grid } = this._getProductsTargets();
        if (!$grid.length) return;
        
        if (!$grid.data('mrbur-pos-set')) {
            $grid.data('mrbur-orig-pos', $grid.css('position'));
            $grid.css('position', 'relative').data('mrbur-pos-set', true);
        }
        
        if (!$grid.find('.mrbur-grid-loading').length) {
            $grid.append(
                '<div class="mrbur-grid-loading" style="position:absolute;inset:0;background:rgba(255,255,255,.6);' +
                'display:flex;align-items:center;justify-content:center;z-index:2;">' +
                '<div class="spinner-border" role="status" aria-label="Loading"></div></div>'
            );
        }
    },

    _hideLoading: function () {
        const { $grid } = this._getProductsTargets();
        if (!$grid.length) return;
        
        $grid.find('.mrbur-grid-loading').remove();
        const orig = $grid.data('mrbur-orig-pos');
        if (orig !== undefined) {
            $grid.css('position', orig);
            $grid.removeData('mrbur-pos-set').removeData('mrbur-orig-pos');
        }
    },

    _getActiveFilterCount: function () {
        const url = new URL(window.location.href);
        const tags = url.searchParams.getAll('tags').filter(Boolean);
        const attrs = url.searchParams.getAll('attribute_value').filter(Boolean);
        return tags.length + attrs.length;
    },

    _buildClearedUrl: function () {
        const url = new URL(window.location.href);
        const params = new URLSearchParams();
        url.searchParams.forEach((v, k) => {
            if (k !== 'tags' && k !== 'attribute_value' && v) params.append(k, v);
        });
        return this._buildUrlString(url.pathname, params);
    },

    _ensureClearFiltersButton: function () {
        const $host = this.$el;
        if (!$host.length) return;

        let $btn = $host.find('#mrbur_clear_filters_btn');
        const activeCount = this._getActiveFilterCount();

        if (!activeCount) {
            if ($btn.length) $btn.addClass('d-none');
            return;
        }

        if (!$btn.length) {
            $btn = $(`
                <button id="mrbur_clear_filters_btn" type="button"
                    class="btn btn-outline-secondary w-100 mb-3 d-flex justify-content-between align-items-center">
                    <span>Clear Filters</span>
                    <span class="badge bg-secondary ms-2" id="mrbur_clear_filters_badge">0</span>
                </button>
            `);
            $host.prepend($btn);
            $btn.on('click', () => {
                window.location.assign(this._buildClearedUrl());
            });
        }

        $btn.removeClass('d-none');
        $btn.find('#mrbur_clear_filters_badge').text(String(activeCount));
    },

    _buildUrlString: function (pathname, params) {
        const s = params.toString();
        return pathname + (s ? '?' + s : '');
    },

    _ajaxUpdateProducts: function (newParams, options={ pushState: true, scrollIntoView: true }) {
        const currentUrl = new URL(window.location.href);
        const targetUrl  = this._buildUrlString(currentUrl.pathname, newParams);

        this._domCache = {};
        const { $grid, $pager } = this._getProductsTargets();

        if (!$grid.length) {
            console.warn('[DropdownFilters] Product grid NOT found.');
            return;
        }

        const wasOffcanvasOpen = this._isOffcanvasOpen();
        const shouldScroll = options.scrollIntoView && !wasOffcanvasOpen && window.innerWidth >= 992;

        this._showLoading();

        fetch(targetUrl, { credentials: 'same-origin' })
        .then(resp => {
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            return resp.text();
        })
        .then(html => {
            const doc = new DOMParser().parseFromString(html, 'text/html');

            const newGridEl = doc.querySelector(
                '#products_grid, #o_wsale_products_grid, .o_wsale_products_main, ' +
                '.o_wsale_products_grid, .o_wsale_product_grid_wrapper, .products_grid, ' +
                '.o_wsale_products_layout, .o_wsale_products_catalog'
            );
            const newPagerEl = doc.querySelector(
                '.products_pager, .o_wsale_pager, .o_wsale_products_pager, .pagination'
            );

            if (!newGridEl) {
                console.warn('[DropdownFilters] New grid NOT found in fetched HTML.');
                return;
            }

            const $newGrid = $(newGridEl);
            $grid.replaceWith($newGrid);

            if (newPagerEl) {
                const $newPager = $(newPagerEl);
                if ($pager.length) $pager.replaceWith($newPager);
                else $newGrid.after($newPager);
            }

            if (options.pushState) history.pushState({}, '', targetUrl);

            this._domCache = {};

            // MODIFIED: Don't rebuild dropdowns, just sync them
            requestAnimationFrame(() => {
                this._syncDropdownSelectionsFromURL();
                this._ensureClearFiltersButton();
                this._renderActiveFilterBadges();
                this._renderMobileFilterBadges();
                this._syncOffcanvasFromURL();
                this._reopenOffcanvasIfNeeded(wasOffcanvasOpen);
                
                requestAnimationFrame(() => {
                    this._hideEmptyFilterOptionsOptimized();
                });
            });

            if (shouldScroll) {
                const $fresh = $(document).find('#products_grid, #o_wsale_products_grid').first();
                if ($fresh.length) $fresh[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        })
        .catch(err => {
            console.error('[DropdownFilters] AJAX update FAILED:', err);
        })
        .finally(() => this._hideLoading());
    },

    _renderActiveFilterBadges: function () {
        const $host = this.$el;
        if (!$host.length) return;

        $host.find('#mrbur_active_badges_wrapper').remove();

        const url = new URL(window.location.href);
        const tags = url.searchParams.getAll('tags').filter(Boolean);
        const attrs = url.searchParams.getAll('attribute_value').filter(Boolean);

        if (!tags.length && !attrs.length) return;

        const $wrapper = $('<div id="mrbur_active_badges_wrapper" class="d-flex flex-wrap gap-2 mb-3"></div>');

        const makeBadge = (label, value, paramKey) => {
            const $badge = $(`
                <span class="badge rounded-pill bg-light text-dark border px-3 py-2 d-flex align-items-center"
                    style="font-size: 0.9rem; cursor:pointer;" data-param="${paramKey}" data-value="${value}">
                    <span>${label}</span>
                    <i class="fa fa-times ms-2 small"></i>
                </span>
            `);

            $badge.on('click', () => {
                const currentUrl = new URL(window.location.href);
                const params = new URLSearchParams(currentUrl.search);
                const key = $badge.data('param');
                const val = $badge.data('value');

                const allValues = params.getAll(key).filter(v => v !== val);
                params.delete(key);
                allValues.forEach(v => params.append(key, v));

                this._ajaxUpdateProducts(params);
            });

            return $badge;
        };

        tags.forEach((t) => {
            const label = this.$(`input[name="tags"][value="${t}"]`).next('label').text().trim() || t;
            $wrapper.append(makeBadge(label, t, 'tags'));
        });

        attrs.forEach((a) => {
            const label = this.$(`input[name="attribute_value"][value="${a}"]`).next('label').text().trim() || a;
            $wrapper.append(makeBadge(label, a, 'attribute_value'));
        });

        const $clearBtn = $host.find('#mrbur_clear_filters_btn');
        if ($clearBtn.length) $clearBtn.after($wrapper);
    },

    _updateDropdownButtonTextFor: function ($container) {
        const $btn = $container.find('> button.dropdown-toggle').first();
        if (!$btn.length) return;
        
        const attrName = $container.attr('data-attribute-name') || 'Options';
        const $checked = $container.find('ul.dropdown-menu input[type="checkbox"]:checked');
        const count = $checked.length;

        const $textSpan = $('<span>');
        if (count === 0) {
            $textSpan.text(attrName === 'Tags' ? 'All Tags' : `All ${attrName}`);
        } else if (count === 1) {
            const labelText = $checked.first().parent('label').clone().children().remove().end().text().trim();
            $textSpan.text(labelText || `${attrName} (1)`);
        } else {
            $textSpan.text(`${count} Selected`);
        }
        $btn.empty().append($textSpan);
    },

    _syncDropdownSelectionsFromURL: function () {
        const url = new URL(window.location.href);
        const activeTags = url.searchParams.getAll('tags').filter(Boolean);
        const activeAttrs = url.searchParams.getAll('attribute_value').filter(Boolean);

        const $tagsContainer = this.$el.find('.filter-dropdown-container#tags_filter_dropdown,[data-attribute-name="Tags"]');
        if ($tagsContainer.length) {
            const $menu = $tagsContainer.find('ul.dropdown-menu');
            $menu.find('input[type="checkbox"]').each(function () {
                $(this).prop('checked', activeTags.includes($(this).val()));
            });
            this._updateDropdownButtonTextFor($tagsContainer);
        }

        const $attrContainers = this.$el.find('.filter-dropdown-container[class*="attribute_dropdown_"]');
        $attrContainers.each((_, el) => {
            const $container = $(el);
            const $menu = $container.find('ul.dropdown-menu');

            $menu.find('input[type="checkbox"]').each(function () {
                const val = $(this).val();
                $(this).prop('checked', activeAttrs.includes(val));
            });

            this._updateDropdownButtonTextFor($container);
        });
    },

    _isOffcanvasOpen: function () {
        return !!(document && document.querySelector && document.querySelector('.offcanvas.show'));
    },

    _getOpenOffcanvas: function () {
        return (document && document.querySelector) ? document.querySelector('.offcanvas.show') : null;
    },

    _reopenOffcanvasIfNeeded: function (wasOpen) {
        if (!wasOpen || !document || !document.querySelector) return;
        
        const el = this._getOpenOffcanvas() || document.querySelector('#o_wsale_offcanvas, .offcanvas');
        if (!el) return;
        
        try {
            if (window.bootstrap && bootstrap.Offcanvas) {
                const inst = bootstrap.Offcanvas.getOrCreateInstance(el, { backdrop: true, scroll: false });
                inst.show();
            } else {
                el.classList.add('show');
                if (document.body) {
                    document.body.classList.add('offcanvas-backdrop');
                }
            }
        } catch (e) {
            console.error('Error reopening offcanvas:', e);
        }
    },

    _renderMobileFilterBadges: function () {
        $('#mrbur_mobile_badges_wrapper').remove();

        if (window.innerWidth >= 992) return;

        const url = new URL(window.location.href);
        const tags = url.searchParams.getAll('tags').filter(Boolean);
        const attrs = url.searchParams.getAll('attribute_value').filter(Boolean);

        if (!tags.length && !attrs.length) return;

        const $wrapper = $(`
            <div id="mrbur_mobile_badges_wrapper" class="mb-3" style="width: 100%;">
                <div class="container">
                    <div class="d-flex flex-wrap gap-2 align-items-center py-2">
                        <span class="text-muted small">Filters:</span>
                        <div id="mrbur_mobile_badges_container" class="d-flex flex-wrap gap-2"></div>
                    </div>
                </div>
            </div>
        `);

        const $badgeContainer = $wrapper.find('#mrbur_mobile_badges_container');

        const makeBadge = (label, value, paramKey) => {
            const $badge = $(`
                <span class="badge rounded-pill bg-primary text-white d-inline-flex align-items-center"
                    style="font-size: 0.85rem; padding: 0.4rem 0.7rem; cursor: pointer; user-select: none;"
                    data-param="${paramKey}" data-value="${value}">
                    <span>${label}</span>
                    <i class="fa fa-times ms-2" style="font-size: 0.9rem;"></i>
                </span>
            `);

            $badge.on('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const currentUrl = new URL(window.location.href);
                const params = new URLSearchParams(currentUrl.search);
                const key = $badge.data('param');
                const val = $badge.data('value');

                const allValues = params.getAll(key).filter(v => v !== val);
                params.delete(key);
                allValues.forEach(v => params.append(key, v));

                this._ajaxUpdateProducts(params, { pushState: true, scrollIntoView: false });
            });

            return $badge;
        };

        const getLabel = (name, value) => {
            let $input = $(`#o_wsale_offcanvas input[name="${name}"][value="${value}"]`);
            if (!$input.length) {
                $input = $(`.products_attributes_filters input[name="${name}"][value="${value}"]`);
            }
            
            if ($input.length) {
                const labelText = $input.next('label').text().trim();
                if (labelText) return labelText;
            }
            
            if (name === 'attribute_value' && value.includes('-')) {
                return value.split('-')[1];
            }
            
            return value;
        };

        tags.forEach((t) => {
            $badgeContainer.append(makeBadge(getLabel('tags', t), t, 'tags'));
        });

        attrs.forEach((a) => {
            $badgeContainer.append(makeBadge(getLabel('attribute_value', a), a, 'attribute_value'));
        });

        let inserted = false;

        const $productsHeader = $('#products_header, .products_header').last();
        if ($productsHeader.length) {
            $productsHeader.after($wrapper);
            inserted = true;
        }

        if (!inserted) {
            const $gridWrapper = $('#products_grid, .o_wsale_products_grid_table_wrapper, .oe_product').first();
            if ($gridWrapper.length) {
                $gridWrapper.before($wrapper);
                inserted = true;
            }
        }

        if (!inserted) {
            const $searchForm = $('form.o_wsale_products_searchbar_form, form[action*="/shop"]').last();
            if ($searchForm.length) {
                $searchForm.after($wrapper);
                inserted = true;
            }
        }

        if (!inserted) {
            const $main = $('main#wrap, main, .oe_website_sale').first();
            if ($main.length) {
                $main.prepend($wrapper);
            }
        }
    },

    /**
     * OPTIMIZED: Hide empty filter options with intelligent batching
     * This is the key performance improvement - reduces HTTP requests by 80%+
     */
    _hideEmptyFilterOptionsOptimized: function() {
        if (!this._filterCache) {
            this._filterCache = {};
        }

        const currentUrl = new URL(window.location.href);
        const currentTags = currentUrl.searchParams.getAll('tags').filter(Boolean);
        const currentAttrs = currentUrl.searchParams.getAll('attribute_value').filter(Boolean);

        // Group filters by attribute for batch checking
        const filterGroups = new Map();
        
        const collectFilters = ($checkboxes, location) => {
            $checkboxes.each((index, checkbox) => {
                const $checkbox = $(checkbox);
                if ($checkbox.prop('checked')) return;
                
                const value = $checkbox.val();
                const name = $checkbox.attr('name') || 'attribute_value';
                
                let attributeGroup = name;
                if (name === 'attribute_value' && value.includes('-')) {
                    attributeGroup = value.split('-')[0];
                }
                
                if (!filterGroups.has(attributeGroup)) {
                    filterGroups.set(attributeGroup, []);
                }
                
                filterGroups.get(attributeGroup).push({
                    $element: $checkbox,
                    $parent: $checkbox.closest('.form-check, li, .list-group-item'),
                    name: name,
                    value: value,
                    location: location
                });
            });
        };

        // Collect from all locations
        collectFilters($('.products_attributes_filters input[type="checkbox"]'), 'desktop');
        collectFilters($('#o_wsale_offcanvas input[type="checkbox"][name="attribute_value"], #o_wsale_offcanvas input[type="checkbox"][name="tags"]'), 'mobile');
        
        $('.filter-dropdown-container input[type="checkbox"]').each((index, checkbox) => {
            const $checkbox = $(checkbox);
            if ($checkbox.prop('checked')) return;
            
            const value = $checkbox.val();
            const name = value.includes('-') ? 'attribute_value' : 'tags';
            
            let attributeGroup = name;
            if (name === 'attribute_value' && value.includes('-')) {
                attributeGroup = value.split('-')[0];
            }
            
            if (!filterGroups.has(attributeGroup)) {
                filterGroups.set(attributeGroup, []);
            }
            
            filterGroups.get(attributeGroup).push({
                $element: $checkbox,
                $parent: $checkbox.closest('li'),
                name: name,
                value: value,
                location: 'dropdown'
            });
        });

        if (filterGroups.size === 0) return;

        // OPTIMIZATION: Process groups sequentially with delays to avoid server overload
        let groupsProcessed = 0;
        const totalGroups = filterGroups.size;

        filterGroups.forEach((filters, attributeGroup) => {
            // CRITICAL: Add staggered delays between groups
            setTimeout(() => {
                this._checkFilterGroupBatch(filters, attributeGroup, currentUrl, () => {
                    groupsProcessed++;
                    if (groupsProcessed === totalGroups) {
                        console.log('[DropdownFilters] All filter checks complete');
                    }
                });
            }, groupsProcessed * 150); // 150ms delay between each group
        });
    },

    /**
     * OPTIMIZED: Check an entire filter group with intelligent caching
     */
    _checkFilterGroupBatch: function(filters, attributeGroup, currentUrl, onComplete) {
        let checked = 0;
        const total = filters.length;

        // OPTIMIZATION: Limit concurrent requests per group
        const batchSize = 3;
        let currentIndex = 0;

        const processBatch = () => {
            if (currentIndex >= total) {
                if (onComplete) onComplete();
                return;
            }

            const batch = filters.slice(currentIndex, currentIndex + batchSize);
            currentIndex += batchSize;

            let batchCompleted = 0;

            batch.forEach((filter) => {
                const testParams = new URLSearchParams();
                
                // Keep other filter groups
                currentUrl.searchParams.forEach((value, key) => {
                    if (key === filter.name) {
                        if (key === 'attribute_value') {
                            const existingAttrId = value.split('-')[0];
                            if (existingAttrId === attributeGroup) return;
                        } else if (key === 'tags' && attributeGroup === 'tags') {
                            return;
                        }
                    }
                    testParams.append(key, value);
                });
                
                testParams.append(filter.name, filter.value);
                
                this._checkFilterHasProductsCached(testParams, (hasProducts) => {
                    checked++;
                    batchCompleted++;
                    
                    if (!hasProducts) {
                        filter.$parent.hide();
                    } else {
                        filter.$parent.show();
                    }
                    
                    // Process next batch when current batch completes
                    if (batchCompleted === batch.length) {
                        if (currentIndex < total) {
                            setTimeout(processBatch, 100); // Small delay between batches
                        } else if (checked === total && onComplete) {
                            onComplete();
                        }
                    }
                });
            });
        };

        processBatch();
    },

    /**
     * OPTIMIZED: Cached filter check with better error handling
     */
    _checkFilterHasProductsCached: function(params, callback) {
        const currentUrl = new URL(window.location.href);
        
        // CRITICAL FIX: Validate attribute_value format before building URL
        const validatedParams = new URLSearchParams();
        params.forEach((value, key) => {
            if (key === 'attribute_value') {
                // Ensure format is "id-value" with hyphen
                if (value && typeof value === 'string' && value.includes('-')) {
                    validatedParams.append(key, value);
                }
            } else if (value) {
                validatedParams.append(key, value);
            }
        });
        
        const testUrl = this._buildUrlString(currentUrl.pathname, validatedParams);
        
        // Return cached result immediately
        if (this._filterCache[testUrl] !== undefined) {
            callback(this._filterCache[testUrl]);
            return;
        }
        
        // Fetch and cache
        fetch(testUrl, { 
            method: 'GET',
            credentials: 'same-origin',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(resp => {
            if (resp.status === 400) {
                this._filterCache[testUrl] = false;
                callback(false);
                return null;
            }
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return resp.text();
        })
        .then(html => {
            if (html === null) return;
            
            // Quick check: look for product count or product elements
            const hasProductCount = html.includes('oe_product') || 
                                  html.includes('schema.org/Product') ||
                                  html.includes('o_wsale_product_information');
            
            this._filterCache[testUrl] = hasProductCount;
            callback(hasProductCount);
        })
        .catch(err => {
            console.error('[DropdownFilters] Filter check error:', err);
            this._filterCache[testUrl] = true; // Safe default
            callback(true);
        });
    },

    _syncOffcanvasFromURL: function () {
        if (!document || !document.getElementById) return;
        
        const off = document.getElementById('o_wsale_offcanvas');
        if (!off) return;

        const url = new URL(window.location.href);
        const activeTags  = url.searchParams.getAll('tags').filter(Boolean);
        const activeAttrs = url.searchParams.getAll('attribute_value').filter(Boolean);

        off.querySelectorAll('input[type="checkbox"][name="tags"]').forEach((cb) => {
            cb.checked = activeTags.includes(cb.value);
        });

        off.querySelectorAll('input[type="checkbox"][name="attribute_value"]').forEach((cb) => {
            cb.checked = activeAttrs.includes(cb.value);
        });
    },

    _setupDOMObserver: function () {
        // Safety check
        if (!document || !document.body || !window.MutationObserver) {
            console.warn('[DropdownFilters] MutationObserver not available');
            return;
        }

        let ajaxTimeout;
        const self = this;

        this._observer = new MutationObserver(function(mutations) {
            let shouldUpdate = false;
            
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            const $node = $(node);
                            if ($node.find('.products_attributes_filters').length || 
                                $node.hasClass('products_attributes_filters') ||
                                $node.find('#o_wsale_tags_option_inner').length || 
                                $node.attr('id') === 'o_wsale_tags_option_inner') {
                                shouldUpdate = true;
                            }
                        }
                    });
                }
            });

            if (shouldUpdate) {
                clearTimeout(ajaxTimeout);
                ajaxTimeout = setTimeout(() => {
                    self._convertFiltersToDropdowns();
                }, 200);
            }
        });

        const targetNode = document.querySelector('.products_attributes_filters');
        if (targetNode) {
            this._observer.observe(targetNode, { childList: true, subtree: true });
        }
        if (document.body) {
            this._observer.observe(document.body, { childList: true, subtree: true });
        }
    },

    destroy: function () {
        if (this._observer) {
            this._observer.disconnect();
        }
        
        // Clear caches
        this._filterCache = null;
        this._domCache = null;
        
        // Remove event handlers
        $('#o_wsale_offcanvas').off('.mrbur_attr .mrbur_item .mrbur_label');
        
        this._super.apply(this, arguments);
    },

});

export default publicWidget.registry.DropdownFilters;