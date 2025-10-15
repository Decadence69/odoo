/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.DropdownFilters = publicWidget.Widget.extend({
    selector: '.products_attributes_filters',
    
    /**
     * Initialize the widget
     */
    start: function () {
        this._super.apply(this, arguments);
        this._convertFiltersToDropdowns();
        this._setupDOMObserver();
    },

    /**
     * Convert all filters to dropdowns
     */
    _convertFiltersToDropdowns: function () {
        this._convertTagsToDropdown();
        this._convertAttributesToDropdown();
    },

    /**
     * Convert Tags to Dropdown with Checkboxes
     */
    _convertTagsToDropdown: function () {
        const $tagsSection = this.$('#o_wsale_tags_option_inner').closest('.accordion-item');

        if (!$tagsSection.length) {
            return;
        }

        const $checkboxes = $tagsSection.find('input[type="checkbox"][name="tags"]');
        
        if (!$checkboxes.length || $tagsSection.find('#tags_filter_dropdown').length) {
            return;
        }

        const urlParams = new URLSearchParams(window.location.search);
        const selectedTags = urlParams.getAll('tags').filter(v => v);

        const $dropdownContainer = this._createDropdownContainer('tags_filter_dropdown');
        const $dropdownButton = this._createDropdownButton();

        const updateButtonText = () => {
            const checkedCount = $dropdownContainer.find('input[type="checkbox"]:checked').length;
            $dropdownButton.empty();
            
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
            
            $dropdownButton.append($textSpan);
        };

        const applyFilters = () => {
            const selectedValues = [];
            $dropdownMenu.find('input[type="checkbox"]:checked').each(function() {
                selectedValues.push($(this).val());
            });

            const currentUrl = new URL(window.location.href);
            const newParams = new URLSearchParams();

            currentUrl.searchParams.forEach((value, key) => {
                if (key !== 'tags' && value) {
                    newParams.append(key, value);
                }
            });

            selectedValues.forEach(function(value) {
                newParams.append('tags', value);
            });

            const paramString = newParams.toString();
            const cleanUrl = currentUrl.pathname + (paramString ? '?' + paramString : '');

            window.location.href = cleanUrl;
        };

        const $dropdownMenu = this._createDropdownMenu($checkboxes, selectedTags, updateButtonText, applyFilters);

        updateButtonText();

        $dropdownContainer.append($dropdownButton);
        $dropdownContainer.append($dropdownMenu);

        const $checkboxContainer = $tagsSection.find('.flex-column');
        if ($checkboxContainer.length) {
            $checkboxContainer.hide();
            $checkboxContainer.before($dropdownContainer);
        }

        $dropdownMenu.on('click', (e) => e.stopPropagation());
    },

    /**
     * Convert Attributes to Dropdown with Checkboxes
     */
    _convertAttributesToDropdown: function () {
        const $attributeSections = this.$('.accordion-item').not(':has(.filter-dropdown-container[class*="attribute_dropdown_"])');

        $attributeSections.each((index, section) => {
            const $section = $(section);
            
            if ($section.find('#o_wsale_tags_option_inner').length) {
                return;
            }

            const $attributeTitle = $section.find('.accordion-header b');
            const attributeName = $attributeTitle.text().trim();

            if (!attributeName) {
                return;
            }

            const $checkboxes = $section.find('input[type="checkbox"][name="attribute_value"]');
            
            if (!$checkboxes.length) {
                return;
            }

            const dropdownClass = 'attribute_dropdown_' + attributeName.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '');

            if ($section.find('.' + dropdownClass).length) {
                return;
            }

            const firstOptionValue = $checkboxes.first().val();
            const thisAttributeId = firstOptionValue ? firstOptionValue.split('-')[0] : null;

            const urlParams = new URLSearchParams(window.location.search);
            const selectedAttributes = urlParams.getAll('attribute_value').filter(v => v);

            const $dropdownContainer = this._createDropdownContainer(dropdownClass);
            $dropdownContainer.attr('data-attribute-id', thisAttributeId);

            const $dropdownButton = this._createDropdownButton();

            const updateButtonText = () => {
                const checkedCount = $dropdownContainer.find('input[type="checkbox"]:checked').length;
                $dropdownButton.empty();
                
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
                
                $dropdownButton.append($textSpan);
            };

            const applyFilters = () => {
                const selectedValues = [];
                $dropdownMenu.find('input[type="checkbox"]:checked').each(function() {
                    selectedValues.push($(this).val());
                });

                const currentUrl = new URL(window.location.href);
                const newParams = new URLSearchParams();

                const currentAttributes = currentUrl.searchParams.getAll('attribute_value').filter(v => v);

                currentUrl.searchParams.forEach((value, key) => {
                    if (key !== 'attribute_value' && value) {
                        newParams.append(key, value);
                    }
                });

                currentAttributes.forEach(function(attr) {
                    const attrId = attr.split('-')[0];
                    if (attrId !== thisAttributeId) {
                        newParams.append('attribute_value', attr);
                    }
                });

                selectedValues.forEach(function(value) {
                    newParams.append('attribute_value', value);
                });

                const paramString = newParams.toString();
                const cleanUrl = currentUrl.pathname + (paramString ? '?' + paramString : '');

                window.location.href = cleanUrl;
            };

            const $dropdownMenu = this._createDropdownMenu($checkboxes, selectedAttributes, updateButtonText, applyFilters);

            // Assemble dropdown first
            $dropdownContainer.append($dropdownButton);
            $dropdownContainer.append($dropdownMenu);

            // Update button text AFTER menu is added to container
            updateButtonText();

            const $checkboxContainer = $section.find('.flex-column');
            if ($checkboxContainer.length) {
                $checkboxContainer.hide();
                $checkboxContainer.before($dropdownContainer);
            }

            $dropdownMenu.on('click', (e) => e.stopPropagation());
        });
    },

    /**
     * Create dropdown container
     */
    _createDropdownContainer: function (className) {
        return $('<div>', {
            class: 'dropdown mb-3 filter-dropdown-container ' + className
        });
    },

    /**
     * Create dropdown button
     */
    _createDropdownButton: function () {
        return $('<button>', {
            class: 'btn btn-light dropdown-toggle w-100 d-flex justify-content-between align-items-center',
            type: 'button',
            'data-bs-toggle': 'dropdown',
            'aria-expanded': 'false',
            style: 'padding: 8px 12px;'
        });
    },

    /**
     * Create dropdown menu with checkboxes
     */
    _createDropdownMenu: function ($checkboxes, selectedValues, updateButtonText, applyFilters) {
        const $dropdownMenu = $('<ul>', {
            class: 'dropdown-menu w-100'
        });

        // Clear All button
        const $clearItem = $('<li>');
        const $clearButton = $('<button>', {
            class: 'dropdown-item text-danger',
            type: 'button',
            text: 'Clear All'
        });
        $clearButton.on('click', (e) => {
            e.preventDefault();
            $dropdownMenu.find('input[type="checkbox"]').prop('checked', false);
            updateButtonText();
            applyFilters();
        });
        $clearItem.append($clearButton);
        $dropdownMenu.append($clearItem);
        $dropdownMenu.append($('<li><hr class="dropdown-divider"></li>'));

        // Checkbox items
        $checkboxes.each((index, checkbox) => {
            const $checkbox = $(checkbox);
            const $label = $checkbox.next('label');
            const itemName = $label.text().trim();
            const itemValue = $checkbox.val();
            const isChecked = $checkbox.prop('checked') || selectedValues.includes(itemValue);

            const $item = $('<li>');
            const $itemLabel = $('<label>', {
                class: 'dropdown-item mb-0'
            });

            const $newCheckbox = $('<input>', {
                type: 'checkbox',
                value: itemValue,
                checked: isChecked,
                class: 'form-check-input'
            });

            $newCheckbox.on('change', (e) => {
                e.stopPropagation();
                updateButtonText();
            });

            $itemLabel.append($newCheckbox);
            $itemLabel.append(document.createTextNode(' ' + itemName));
            $item.append($itemLabel);
            $dropdownMenu.append($item);
        });

        // Apply button
        const $applyItem = $('<li>');
        const $applyButton = $('<button>', {
            class: 'dropdown-item apply-filter-btn',
            type: 'button',
            text: 'Apply Filters'
        });
        $applyButton.on('click', (e) => {
            e.preventDefault();
            applyFilters();
        });
        $dropdownMenu.append($('<li><hr class="dropdown-divider"></li>'));
        $applyItem.append($applyButton);
        $dropdownMenu.append($applyItem);

        return $dropdownMenu;
    },

    /**
     * Setup DOM observer for AJAX updates
     */
    _setupDOMObserver: function () {
        let ajaxTimeout;
        const self = this;
        
        // Use MutationObserver instead of deprecated DOMNodeInserted
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) { // Element node
                            const $node = $(node);
                            if ($node.find('.products_attributes_filters').length || 
                                $node.hasClass('products_attributes_filters') ||
                                $node.find('#o_wsale_tags_option_inner').length || 
                                $node.attr('id') === 'o_wsale_tags_option_inner') {
                                clearTimeout(ajaxTimeout);
                                ajaxTimeout = setTimeout(() => {
                                    self._convertFiltersToDropdowns();
                                }, 200);
                            }
                        }
                    });
                }
            });
        });

        // Observe the entire products attributes filters section (safe check)
        const targetNode = document.querySelector('.products_attributes_filters');
        if (targetNode) {
            observer.observe(targetNode, {
                childList: true,
                subtree: true
            });
        }
        
        // Always observe body for any new filter sections (document.body is always safe)
        if (document.body) {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }
    },
});

export default publicWidget.registry.DropdownFilters;