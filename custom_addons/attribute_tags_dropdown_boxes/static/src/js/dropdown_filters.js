import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.DropdownFilters = publicWidget.Widget.extend({
    selector: '.products_attributes_filters',

    _filterCache: null,
    _filterCheckQueue: null,
    _isCheckingFilters: false,
    _domCache: {},
    _pendingRequest: null,
    _productCache: {},
    _lastFetchTime: 0,
    _abortController: null,
    _batchValidationCache: null,
    _pendingBatchRequest: null,

    start: function () {
        this._super.apply(this, arguments);

        if (this._isEditMode()) {
            return;
        }

        if (!document || !document.body) {
            setTimeout(() => this.start(), 100);
            return;
        }

        this._filterCache = {};
        this._batchValidationCache = {};
        this._domCache = {};
        
        const $form = this.$el.closest('form');
        if ($form.length) {
            $form.off('submit.mrbur').on('submit.mrbur', (e) => {
                e.preventDefault(); 
                e.stopPropagation(); 
                return false;
            });
        }

        // Priority 1: Critical UI setup
        this._setupOffcanvasHandlers();
        this._setupFilterHandlers();
        this._setupDynamicFilterUpdates();

        // Priority 2: Dropdown conversion
        requestAnimationFrame(() => {
            this._convertFiltersToDropdowns();
            this._ensureClearFiltersButton();
            this._renderActiveFilterBadges();
        });
        
        // Priority 3: Non-critical features
        if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {
                this._setupDOMObserver();
                this._renderMobileFilterBadges();
                this._setupLazyFilterCheck();
                this._enableLazyLoadingForProducts();
            }, { timeout: 1000 });
        } else {
            setTimeout(() => {
                this._setupDOMObserver();
                this._renderMobileFilterBadges();
                this._setupLazyFilterCheck();
                this._enableLazyLoadingForProducts();
            }, 500);
        }

        window.addEventListener('popstate', () => {
            this._handlePopState();
        });

        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this._renderMobileFilterBadges();
            }, 250);
        });
    },

    _isEditMode: function() {
        return document.body.classList.contains('editor_enable') ||
               document.body.classList.contains('editor_has_snippets') ||
               typeof odoo !== 'undefined' && odoo.isReady === false ||
               window.location.search.includes('enable_editor=1');
    },

    _batchValidateFilters: function(callback) {
        if (this._isEditMode()) return;
        
        if (this._pendingBatchRequest) {
            return;
        }

        const currentUrl = new URL(window.location.href);
        const currentState = this._getCurrentFilterState();
        const cacheKey = this._getBatchCacheKey(currentState);

        // Check cache
        if (this._batchValidationCache[cacheKey]) {
            const cached = this._batchValidationCache[cacheKey];
            if (Date.now() - cached.timestamp < 30000) {
                callback(cached.data);
                return;
            }
        }

        const allFilters = this._collectAllFilterOptions();
        
        if (allFilters.length === 0) {
            callback({});
            return;
        }

        const payload = {
            current_filters: currentState,
            check_filters: allFilters,
            path: currentUrl.pathname
        };

        const jsonRpcPayload = {
            jsonrpc: '2.0',
            method: 'call',
            params: payload,
            id: Math.floor(Math.random() * 1000000)
        };

        this._pendingBatchRequest = true;

        fetch('/shop/filters/batch_validate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin',
            body: JSON.stringify(jsonRpcPayload)
        })
        .then(resp => {
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return resp.json();
        })
        .then(data => {
            let validCombinations = {};
            if (data.result && data.result.valid_combinations) {
                validCombinations = data.result.valid_combinations;
            } else if (data.valid_combinations) {
                validCombinations = data.valid_combinations;
            }
            
            this._batchValidationCache[cacheKey] = {
                data: validCombinations,
                timestamp: Date.now()
            };
            
            callback(validCombinations);
        })
        .catch(err => {
            console.error('[DropdownFilters] Validation failed:', err);
            callback({});
        })
        .finally(() => {
            this._pendingBatchRequest = false;
        });
    },

    _getCurrentFilterState: function() {
        const url = new URL(window.location.href);
        const tags = url.searchParams.getAll('tags').filter(Boolean);
        const attrs = url.searchParams.getAll('attribute_value').filter(Boolean);
        
        return {
            tags: tags,
            attributes: attrs,
            search: url.searchParams.get('search') || '',
            category: url.searchParams.get('category') || ''
        };
    },

    _getBatchCacheKey: function(state) {
        const sorted_tags = [...state.tags].sort().join(',');
        const sorted_attrs = [...state.attributes].sort().join(',');
        return `${state.category}|${state.search}|${sorted_tags}|${sorted_attrs}`;
    },

    _syncDropdownButtonTextOnly: function() {
        $('.filter-dropdown-container').each((index, container) => {
            const $container = $(container);
            this._updateDropdownButtonTextFor($container);
        });
    },

    _collectAllFilterOptions: function() {
        const filters = [];
        const seen = new Set();

        // Collect from dropdowns
        $('.filter-dropdown-container input[type="checkbox"]').each((index, checkbox) => {
            const $cb = $(checkbox);
            const value = $cb.val();
            const $container = $cb.closest('.filter-dropdown-container');
            
            let name;
            if ($container.attr('id') === 'tags_filter_dropdown' || 
                $container.attr('data-attribute-name') === 'Tags') {
                name = 'tags';
            } else if (value && value.includes('-')) {
                name = 'attribute_value';
            } else {
                return;
            }
            
            const key = `${name}:${value}`;
            if (!seen.has(key) && value) {
                seen.add(key);
                filters.push({ name, value });
            }
        });

        // Collect from offcanvas
        $('#o_wsale_offcanvas input[type="checkbox"]').each((index, checkbox) => {
            const $cb = $(checkbox);
            const name = $cb.attr('name');
            const value = $cb.val();
            const key = `${name}:${value}`;
            
            if (!seen.has(key) && value && (name === 'tags' || name === 'attribute_value')) {
                seen.add(key);
                filters.push({ name, value });
            }
        });

        return filters;
    },

    _hideEmptyFilterOptionsOptimized: function(callback) {
        if (this._isEditMode()) return;
        
        if (this._isCheckingFilters) {
            return;
        }
        
        this._isCheckingFilters = true;

        this._batchValidateFilters((validCombinations) => {
            this._applyFilterVisibility(validCombinations);
            this._updateDropdownStates(validCombinations);
            this._isCheckingFilters = false;
            
            if (typeof callback === 'function') {
                callback();
            }
        });
    },

    _applyFilterVisibility: function(validCombinations) {
        // Desktop filters
        $('.products_attributes_filters input[type="checkbox"]').each((index, checkbox) => {
            const $cb = $(checkbox);
            
            const name = $cb.attr('name');
            if (!name || (name !== 'tags' && name !== 'attribute_value')) {
                return;
            }
            
            if ($cb.prop('checked')) return;
            
            const value = $cb.val();
            const key = `${name}:${value}`;
            
            const $parent = $cb.closest('.form-check, li, .list-group-item');
            
            if (validCombinations[key] === false) {
                $parent.hide();
            } else {
                $parent.show();
            }
        });

        // Mobile offcanvas
        $('#o_wsale_offcanvas input[type="checkbox"]').each((index, checkbox) => {
            const $cb = $(checkbox);
            
            const name = $cb.attr('name');
            if (!name || (name !== 'tags' && name !== 'attribute_value')) {
                return;
            }
            
            if ($cb.prop('checked')) return;
            
            const value = $cb.val();
            const key = `${name}:${value}`;
            
            const $parent = $cb.closest('.form-check, li, .list-group-item');
            
            if (validCombinations[key] === false) {
                $parent.hide();
            } else {
                $parent.show();
            }
        });
    },

    _invalidateBatchCache: function() {
        this._batchValidationCache = {};
    },

    _handlePopState: function() {
        if (this._isEditMode()) return;
        
        if (typeof this._ajaxUpdateProducts === 'function') {
            const url = new URL(window.location.href);
            this._ajaxUpdateProducts(url.searchParams, { pushState: false, scrollIntoView: false });
        }
        this._ensureClearFiltersButton();
        this._renderActiveFilterBadges();
        this._renderMobileFilterBadges();
        this._syncDropdownSelectionsFromURL?.();
        this._syncOffcanvasFromURL();
        this._invalidateBatchCache();
    },

    _setupOffcanvasHandlers: function() {
        if (this._isEditMode()) return;
        
        const offEl = document.getElementById('o_wsale_offcanvas');
        
        if (offEl) {
            offEl.addEventListener('hidden.bs.offcanvas', () => {
                this._forceCleanupStyles();
                setTimeout(() => this._cleanupOffcanvasStyles(), 100);
            }, { passive: true });
            
            offEl.addEventListener('show.bs.offcanvas', () => {
                this._forceCleanupStyles();
            }, { passive: true });
        }
        
        this._cleanupStylesInterval = setInterval(() => {
            if (!document.querySelector('.offcanvas.show') && 
                !document.querySelector('.modal.show')) {
                this._forceCleanupStyles();
            }
        }, 500);
    },
    
    _cleanupOffcanvasStyles: function() {
        if (this._isEditMode()) return;
        
        setTimeout(() => {
            document.body.classList.remove('offcanvas-backdrop', 'offcanvas-open', 'modal-open');
            
            document.querySelectorAll('.offcanvas-backdrop, .modal-backdrop').forEach(backdrop => {
                backdrop.remove();
            });
            
            if (!document.querySelector('.offcanvas.show') &&
                !document.querySelector('.modal.show')) {
                
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
                document.body.style.removeProperty('overflow');
                document.body.style.removeProperty('padding-right');
                document.body.removeAttribute('data-bs-overflow');
                document.body.removeAttribute('data-bs-padding-right');
                
                document.documentElement.style.overflow = '';
                document.documentElement.style.paddingRight = '';
                document.documentElement.style.removeProperty('overflow');
                document.documentElement.style.removeProperty('padding-right');
                
                const htmlStyle = document.documentElement.getAttribute('style');
                if (htmlStyle) {
                    let cleaned = htmlStyle
                        .replace(/padding-right\s*:\s*[^;]+;?/gi, '')
                        .replace(/overflow\s*:\s*[^;]+;?/gi, '')
                        .trim();
                    
                    if (cleaned) {
                        document.documentElement.setAttribute('style', cleaned);
                    } else {
                        document.documentElement.removeAttribute('style');
                    }
                }
                
                const bodyStyle = document.body.getAttribute('style');
                if (bodyStyle) {
                    let cleaned = bodyStyle
                        .replace(/padding-right\s*:\s*[^;]+;?/gi, '')
                        .replace(/overflow\s*:\s*[^;]+;?/gi, '')
                        .trim();
                    
                    if (cleaned) {
                        document.body.setAttribute('style', cleaned);
                    } else {
                        document.body.removeAttribute('style');
                    }
                }
                
                if (window.innerWidth < 992) {
                    document.documentElement.style.overflowX = 'hidden';
                    document.body.style.overflowX = 'hidden';
                    document.body.style.width = '100%';
                    document.body.style.maxWidth = '100vw';
                }
            }
        }, 350);
    },

    _forceCleanupStyles: function() {
        if (this._isEditMode()) return;
        
        document.body.classList.remove('offcanvas-backdrop', 'offcanvas-open', 'modal-open');
        document.querySelectorAll('.offcanvas-backdrop, .modal-backdrop').forEach(el => el.remove());
        
        ['body', 'html'].forEach(selector => {
            const el = selector === 'body' ? document.body : document.documentElement;
            el.style.overflow = '';
            el.style.paddingRight = '';
            el.style.removeProperty('overflow');
            el.style.removeProperty('padding-right');
            
            const style = el.getAttribute('style');
            if (style) {
                let cleaned = style
                    .replace(/padding-right\s*:\s*[^;]+;?/gi, '')
                    .replace(/overflow\s*:\s*[^;]+;?/gi, '')
                    .trim();
                
                if (cleaned) {
                    el.setAttribute('style', cleaned);
                } else {
                    el.removeAttribute('style');
                }
            }
        });
        
        if (window.innerWidth < 992) {
            document.documentElement.style.overflowX = 'hidden';
            document.body.style.overflowX = 'hidden';
            document.body.style.width = '100%';
            document.body.style.maxWidth = '100vw';
        }
    },

    _updateDropdownStates: function(validCombinations) {
        $('.filter-dropdown-container ul.dropdown-menu li').each((index, li) => {
            const $li = $(li);
            const $checkbox = $li.find('input[type="checkbox"]');
            
            const value = $checkbox.val();
            const isChecked = $checkbox.prop('checked');
            const $container = $checkbox.closest('.filter-dropdown-container');
            
            // Always show checked items
            if (isChecked) {
                $li.removeClass('d-none');
                $li.css('display', '');
                return;
            }
            
            let name;
            if ($container.attr('id') === 'tags_filter_dropdown' || 
                $container.attr('data-attribute-name') === 'Tags') {
                name = 'tags';
            } else if (value && value.includes('-')) {
                name = 'attribute_value';
            } else {
                return;
            }
            
            const key = `${name}:${value}`;
            const isValid = validCombinations[key];
            
            if (isValid === false) {
                $li.addClass('d-none');
                $li.css('display', 'none');
            } else {
                $li.removeClass('d-none');
                $li.css('display', '');
            }
        });
    },

    _setupFilterHandlers: function() {
        if (this._isEditMode()) return;
        
        const $off = $('#o_wsale_offcanvas');
        
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

        $off.on('click.mrbur_item', '.list-group-item', (e) => {
            if (this._isEditMode()) return;
            
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
            if (this._isEditMode()) return;
            
            e.preventDefault(); 
            e.stopPropagation();

            const cb = e.currentTarget;
            const isChecked = cb.checked;
            
            cb.toggleAttribute('checked', isChecked);

            this._invalidateBatchCache();
            
            if (this._filterCache) this._filterCache = {}; 

            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                const $offcanvas = $('#o_wsale_offcanvas');
                const selectedValues = [];
                
                $offcanvas.find('input[type="checkbox"][name="attribute_value"]:checked').each(function() {
                    selectedValues.push($(this).val());
                });
                
                const current = new URL(window.location.href);
                const params = new URLSearchParams();
                
                current.searchParams.forEach((val, key) => {
                    if (key !== 'attribute_value' && val) {
                        params.append(key, val);
                    }
                });
                
                selectedValues.forEach((v) => params.append('attribute_value', v));

                if (typeof this._ajaxUpdateProducts === 'function') {
                    this._ajaxUpdateProducts(params, { pushState: true, scrollIntoView: false });
                } else {
                    window.history.pushState({}, '', `${location.pathname}?${params.toString()}`);
                }
            }, 300);
        };
    },

    _debounceTimer: null,
    _debounce: function (fn, delay=250) {
        clearTimeout(this._debounceTimer);
        this._debounceTimer = setTimeout(fn, delay);
    },

    _convertFiltersToDropdowns: function () {
        if (this._isEditMode()) return;
        
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
        
        this._dropdownsCreated = true;
    },

    _convertTagsToDropdown: function () {
        if (this._isEditMode()) return;
        
        const $tagsSection = this.$('#o_wsale_tags_option_inner').closest('.accordion-item');
        if (!$tagsSection.length) return;

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
            this._invalidateBatchCache();
            this._ajaxUpdateProducts(newParams);
        };

        const clearFiltersNavigate = () => {
            const currentUrl = new URL(window.location.href);
            const newParams = new URLSearchParams();
            currentUrl.searchParams.forEach((value, key) => {
                if (key !== 'tags' && value) newParams.append(key, value);
            });
            this._invalidateBatchCache();
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
            $checkboxContainer.remove();
            
            const $accordionBody = $tagsSection.find('.accordion-body');
            if ($accordionBody.length) {
                $accordionBody.prepend($dropdownContainer);
            } else {
                $tagsSection.find('.accordion-collapse').prepend($dropdownContainer);
            }
        }

        $dropdownMenu.on('click', (e) => e.stopPropagation());
    },

    _convertAttributesToDropdown: function () {
        if (this._isEditMode()) return;
        
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
                this._invalidateBatchCache();
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

                this._invalidateBatchCache();
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
                $checkboxContainer.remove();
                
                const $accordionBody = $section.find('.accordion-body');
                if ($accordionBody.length) {
                    $accordionBody.prepend($dropdownContainer);
                } else {
                    $section.find('.accordion-collapse').prepend($dropdownContainer);
                }
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
        const $btn = $('<button>', {
            class: 'btn btn-light dropdown-toggle w-100 d-flex justify-content-between align-items-center',
            type: 'button',
            'data-bs-toggle': 'dropdown',
            'aria-expanded': 'false',
            style: 'padding: 8px 12px;'
        });
        
        return $btn;
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
                
                this._debounce(() => {
                    this._invalidateBatchCache();
                    applyFilters();
                }, 250);
            });

            $itemLabel.append($newCheckbox, document.createTextNode(' ' + itemName));
            $item.append($itemLabel);
            $dropdownMenu.append($item);
        });

        return $dropdownMenu;
    },

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
        if (!$grid || !$grid.length) return;
        
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
        if (!$grid || !$grid.length) return;
        
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
        if (this._isEditMode()) return;
        
        const $host = this.$el;
        if (!$host || !$host.length) return;

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
                this._invalidateBatchCache();
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
        if (this._isEditMode()) return;
        
        if (this._abortController) {
            this._abortController.abort();
        }
        this._abortController = new AbortController();
        
        const currentUrl = new URL(window.location.href);
        const targetUrl  = this._buildUrlString(currentUrl.pathname, newParams);

        const dropdownSelections = this._captureDropdownSelections();

        this._domCache = {};
        const { $grid, $pager } = this._getProductsTargets();

        if (!$grid || !$grid.length) {
            console.warn('[DropdownFilters] Product grid not found');
            return;
        }

        const shouldScroll = options.scrollIntoView && window.innerWidth >= 992;

        this._showLoading();

        fetch(targetUrl, { 
            credentials: 'same-origin',
            signal: this._abortController.signal 
        })
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
                console.warn('[DropdownFilters] New grid not found in fetched HTML');
                return;
            }

            const $newGrid = $(newGridEl);
            $grid.replaceWith($newGrid);

            if (newPagerEl) {
                const $newPager = $(newPagerEl);
                if ($pager && $pager.length) $pager.replaceWith($newPager);
                else $newGrid.after($newPager);
            }

            this._domCache = {};
            
            if (options.pushState) {
                history.pushState({}, '', targetUrl);
            }
            
            requestAnimationFrame(() => {
                this._syncDropdownSelectionsFromURL();
                
                this._ensureClearFiltersButton();
                this._renderActiveFilterBadges();
                this._renderMobileFilterBadges();
                this._syncOffcanvasFromURL();
                
                this._forceCleanupStyles();
                
                setTimeout(() => {
                    this._cleanupOffcanvasStyles();
                }, 100);
                
                this._enableLazyLoadingForProducts();
            });
            
            setTimeout(() => {
                this._invalidateBatchCache();
                
                this._hideEmptyFilterOptionsOptimized(() => {
                    this._syncDropdownSelectionsFromURL();
                });
            }, 500);

            if (shouldScroll) {
                const $fresh = $(document).find('#products_grid, #o_wsale_products_grid').first();
                if ($fresh.length) $fresh[0].scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        })
        .catch(err => {
            if (err.name === 'AbortError') {
                // Request cancelled, silently ignore
            } else {
                console.error('[DropdownFilters] AJAX update failed:', err);
            }
        })
        .finally(() => {
            this._hideLoading();
            this._abortController = null;
        });
    },

    _captureDropdownSelections: function() {
        const selections = {
            tags: [],
            attributes: {}
        };
        
        // Capture tags
        $('.filter-dropdown-container#tags_filter_dropdown input[type="checkbox"]:checked').each(function() {
            selections.tags.push($(this).val());
        });
        
        // Capture attributes by container
        $('.filter-dropdown-container[class*="attribute_dropdown_"]').each(function() {
            const $container = $(this);
            const attrName = $container.attr('data-attribute-name');
            selections.attributes[attrName] = [];
            
            $container.find('input[type="checkbox"]:checked').each(function() {
                selections.attributes[attrName].push($(this).val());
            });
        });
        
        return selections;
    },

    _restoreDropdownSelections: function(selections) {
        if (!selections) return;
        
        // Restore tags
        const $tagsContainer = $('.filter-dropdown-container#tags_filter_dropdown');
        if ($tagsContainer.length && selections.tags.length > 0) {
            $tagsContainer.find('input[type="checkbox"]').each(function() {
                const $cb = $(this);
                const shouldBeChecked = selections.tags.includes($cb.val());
                $cb.prop('checked', shouldBeChecked);
                
                if (shouldBeChecked) {
                    $cb.closest('li').show();
                }
            });
        }
        
        // Restore attributes
        $('.filter-dropdown-container[class*="attribute_dropdown_"]').each(function() {
            const $container = $(this);
            const attrName = $container.attr('data-attribute-name');
            const selectedValues = selections.attributes[attrName] || [];
            
            if (selectedValues.length > 0) {
                $container.find('input[type="checkbox"]').each(function() {
                    const $cb = $(this);
                    const shouldBeChecked = selectedValues.includes($cb.val());
                    $cb.prop('checked', shouldBeChecked);
                    
                    if (shouldBeChecked) {
                        $cb.closest('li').show();
                    }
                });
            }
        });
    },

    _renderActiveFilterBadges: function () {
        if (this._isEditMode()) return;
        
        const $host = this.$el;
        if (!$host || !$host.length) return;

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

                this._invalidateBatchCache();
                
                this._ajaxUpdateProducts(params, { 
                    pushState: true, 
                    scrollIntoView: false 
                });
            });

            return $badge;
        };

        const getLabel = (name, value) => {
            // Try dropdown first
            let $input = $(`.filter-dropdown-container input[type="checkbox"][value="${value}"]`);
            if ($input.length) {
                const labelText = $input.parent('label').clone().children().remove().end().text().trim();
                if (labelText) return labelText;
            }
            
            // Try original filters
            $input = this.$(`input[name="${name}"][value="${value}"]`);
            if ($input.length) {
                const labelText = $input.next('label').text().trim();
                if (labelText) return labelText;
            }
            
            // Try offcanvas
            $input = $(`#o_wsale_offcanvas input[name="${name}"][value="${value}"]`);
            if ($input.length) {
                const labelText = $input.next('label').text().trim();
                if (labelText) return labelText;
            }
            
            // Fallback for attribute values
            if (name === 'attribute_value' && value.includes('-')) {
                const parts = value.split('-');
                return parts[1] || value;
            }
            
            return value;
        };

        tags.forEach((t) => {
            const label = getLabel('tags', t);
            $wrapper.append(makeBadge(label, t, 'tags'));
        });

        attrs.forEach((a) => {
            const label = getLabel('attribute_value', a);
            $wrapper.append(makeBadge(label, a, 'attribute_value'));
        });

        const $clearBtn = $host.find('#mrbur_clear_filters_btn');
        if ($clearBtn.length) $clearBtn.after($wrapper);
    },

    _updateDropdownButtonTextFor: function ($container) {
        if (!$container || !$container.length) return;
        
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
        if (this._isEditMode()) return;
        
        const url = new URL(window.location.href);
        const activeTags = url.searchParams.getAll('tags').filter(Boolean);
        const activeAttrs = url.searchParams.getAll('attribute_value').filter(Boolean);

        const $tagsContainer = this.$el.find('.filter-dropdown-container#tags_filter_dropdown,[data-attribute-name="Tags"]');
        if ($tagsContainer.length) {
            const $menu = $tagsContainer.find('ul.dropdown-menu');
            $menu.find('input[type="checkbox"]').each(function () {
                const $cb = $(this);
                const shouldBeChecked = activeTags.includes($cb.val());
                $cb.prop('checked', shouldBeChecked);
                
                if (shouldBeChecked) {
                    $cb.closest('li').removeClass('d-none').css('display', '');
                }
            });
            this._updateDropdownButtonTextFor($tagsContainer);
        }

        const $attrContainers = this.$el.find('.filter-dropdown-container[class*="attribute_dropdown_"]');
        $attrContainers.each((_, el) => {
            const $container = $(el);
            const $menu = $container.find('ul.dropdown-menu');

            $menu.find('input[type="checkbox"]').each(function () {
                const $cb = $(this);
                const val = $cb.val();
                const shouldBeChecked = activeAttrs.includes(val);
                $cb.prop('checked', shouldBeChecked);
                
                if (shouldBeChecked) {
                    $cb.closest('li').removeClass('d-none').css('display', '');
                }
            });

            this._updateDropdownButtonTextFor($container);
        });
    },

    _renderMobileFilterBadges: function () {
        if (this._isEditMode()) return;
        
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

                this._invalidateBatchCache();
                this._ajaxUpdateProducts(params, { pushState: true, scrollIntoView: false });
            });

            return $badge;
        };

        const getLabel = (name, value) => {
            // Try dropdown first
            let $input = $(`.filter-dropdown-container input[type="checkbox"][value="${value}"]`);
            if ($input.length) {
                const labelText = $input.parent('label').clone().children().remove().end().text().trim();
                if (labelText) return labelText;
            }
            
            // Try offcanvas
            $input = $(`#o_wsale_offcanvas input[name="${name}"][value="${value}"]`);
            if ($input.length) {
                const labelText = $input.next('label').text().trim();
                if (labelText) return labelText;
            }
            
            // Try main filters
            $input = $(`.products_attributes_filters input[name="${name}"][value="${value}"]`);
            if ($input.length) {
                const labelText = $input.next('label').text().trim();
                if (labelText) return labelText;
            }
            
            // Fallback for attribute values
            if (name === 'attribute_value' && value.includes('-')) {
                const parts = value.split('-');
                return parts[1] || value;
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

    _enableLazyLoadingForProducts: function() {
        if (this._isEditMode()) return;
        
        const productImages = document.querySelectorAll(
            '#products_grid img, ' +
            '.o_wsale_products_grid img, ' +
            '.oe_product img, ' +
            '.o_wsale_product_grid_wrapper img'
        );
        
        productImages.forEach(img => {
            if (!img.hasAttribute('loading')) {
                img.setAttribute('loading', 'lazy');
            }
            
            if (!img.hasAttribute('decoding')) {
                img.setAttribute('decoding', 'async');
            }
        });
    },

    _setupLazyFilterCheck: function() {
        if (this._isEditMode()) {
            return;
        }

        // For mobile offcanvas
        const offcanvasEl = document.getElementById('o_wsale_offcanvas');
        if (offcanvasEl) {
            offcanvasEl.addEventListener('shown.bs.offcanvas', () => {
                if (!offcanvasEl.dataset.filtersChecked) {
                    offcanvasEl.dataset.filtersChecked = 'true';
                    this._hideEmptyFilterOptionsOptimized();
                }
            }, { once: true, passive: true });
        }

        // For desktop, use IntersectionObserver
        if ('IntersectionObserver' in window) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !entry.target.dataset.filterChecked) {
                        entry.target.dataset.filterChecked = 'true';
                        this._hideEmptyFilterOptionsOptimized();
                        observer.disconnect();
                    }
                });
            }, { rootMargin: '100px' });

            const filterContainer = document.querySelector('.products_attributes_filters');
            if (filterContainer) {
                observer.observe(filterContainer);
            }
        } else {
            setTimeout(() => this._hideEmptyFilterOptionsOptimized(), 2000);
        }
    },

    _syncOffcanvasFromURL: function () {
        if (this._isEditMode()) return;
        
        if (!document || !document.getElementById) return;
        
        const off = document.getElementById('o_wsale_offcanvas');
        if (!off) return;

        const url = new URL(window.location.href);
        const activeTags  = url.searchParams.getAll('tags').filter(Boolean);
        const activeAttrs = url.searchParams.getAll('attribute_value').filter(Boolean);

        const isOffcanvasVisible = off.classList.contains('show');
        
        if (!isOffcanvasVisible) {
            off.querySelectorAll('input[type="checkbox"][name="tags"]').forEach((cb) => {
                cb.checked = activeTags.includes(cb.value);
            });

            off.querySelectorAll('input[type="checkbox"][name="attribute_value"]').forEach((cb) => {
                cb.checked = activeAttrs.includes(cb.value);
            });
        }
    },

    _setupDynamicFilterUpdates: function() {
        if (this._isEditMode()) return;
        
        // Only for offcanvas - dropdowns have their own handlers
        $(document).on('change.dynamic_filters', '#o_wsale_offcanvas input[type="checkbox"]', (e) => {
            this._invalidateBatchCache();
            
            this._debounce(() => {
                this._hideEmptyFilterOptionsOptimized();
            }, 300);
        });
    },

    _setupDOMObserver: function () {
        if (this._isEditMode()) return;
        
        if (!document || !document.body || !window.MutationObserver) {
            return;
        }

        let ajaxTimeout;
        const self = this;

        this._observer = new MutationObserver(function(mutations) {
            if (self._isEditMode()) return;
            
            let shouldUpdate = false;
            
            for (let mutation of mutations) {
                if (mutation.addedNodes.length) {
                    for (let node of mutation.addedNodes) {
                        if (node.nodeType === 1) {
                            const $node = $(node);
                            if ($node.find('.products_attributes_filters').length || 
                                $node.hasClass('products_attributes_filters') ||
                                $node.find('#o_wsale_tags_option_inner').length || 
                                $node.attr('id') === 'o_wsale_tags_option_inner') {
                                shouldUpdate = true;
                                break;
                            }
                        }
                    }
                }
                if (shouldUpdate) break;
            }

            if (shouldUpdate) {
                clearTimeout(ajaxTimeout);
                ajaxTimeout = setTimeout(() => {
                    self._convertFiltersToDropdowns();
                }, 500);
            }
        });

        const targetNode = document.querySelector('.products_attributes_filters');
        if (targetNode) {
            this._observer.observe(targetNode, { 
                childList: true, 
                subtree: true 
            });
        }
        
        if (document.body) {
            this._observer.observe(document.body, { 
                childList: true, 
                subtree: false
            });
        }
    },

    destroy: function () {
        $(document).off('.dynamic_filters');
        
        if (this._observer) this._observer.disconnect();
        if (this._cleanupStylesInterval) clearInterval(this._cleanupStylesInterval);
        if (this._abortController) this._abortController.abort();
        
        this._filterCache = null;
        this._batchValidationCache = null;
        this._domCache = null;
        
        this._super.apply(this, arguments);
    },

});

export default publicWidget.registry.DropdownFilters;