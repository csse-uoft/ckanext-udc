/**
 * UDC Customized Package Form.
 * Sync CKAN fields with the UDC fields.
 */
this.ckan.module('package-form', function ($) {
    return {
        initialize: function () {
            
            // Initialize Tooltips
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            })

            // Percentages on each maturity level
            this.levels = []; // number of fields in each level
            this.tabs = []; // tab elements for each level
            for (const [i, level] of window.packageConfig.entries()) {
                this.tabs.push(document.querySelector("#maturity_level_" + (i + 1) + "-tab"));
                if (level.fields) {
                    this.levels[i] = {
                        fieldElements: [],
                        progressElement: document.querySelector('#progress-' + (i + 1))
                    }

                    for (const field of level.fields) {
                        if (field.name) {
                            const fieldElement = document.querySelector(`#field-${field.name}`);
                            fieldElement.addEventListener('change', () => this._onFieldChange());
                            this.levels[i].fieldElements.push(fieldElement);

                            // setup select2
                            if (field.type === "multiple_select") {
                                const options = [];
                                const selectedOptions = [];
                                const curr_str = fieldElement.value;
                                const curr = curr_str.split(",");
                                for (const option of field.options) {
                                    const select2Option = {
                                        id: option.value,
                                        text: option.text
                                    }
                                    options.push(select2Option);
                                    if (curr.includes(option.value)) {
                                        selectedOptions.push(select2Option);
                                    }
                                }
                                $(`#field-${field.name}`).select2({
                                    multiple: true, width: 'resolve', data: options, selected: selectedOptions
                                });
                            }
                        } else if (field.ckanField) {
                            if (field.ckanField === "custom_fields") continue;
                            else if (field.ckanField === "organization_and_visibility") {
                                const orgElement = document.querySelector(`#field-organizations`);
                                const visibilityElement = document.querySelector(`#field-private`);
                                this.levels[i].fieldElements.push(orgElement);
                                this.levels[i].fieldElements.push(visibilityElement);
                                orgElement.addEventListener('change', () => this._onFieldChange());
                                visibilityElement.addEventListener('change', () => this._onFieldChange());
                                
                            } else {
                                const fieldElement = document.querySelector(`#field-${field.ckanField}`);
                                this.levels[i].fieldElements.push(fieldElement);
                                fieldElement.addEventListener('change', () => this._onFieldChange());
                            }

                        }
                    }
                }
            }
            // console.log(this)

            // Trigger _onFieldChange to set percentage
            this._onFieldChange();

        },
        _onFieldChange: function() {
            // console.log('updated')
            // Calculate percentage after field changed
            for (const [i, {fieldElements, progressElement}] of this.levels.entries()) {
                let inputtedFields = 0;
                for (const fieldElement of fieldElements) {
                    if (fieldElement.value != null && fieldElement.value !== '') {
                        inputtedFields++;
                    }
                }
                // Update the percentage bar
                const percentage = (inputtedFields / fieldElements.length * 100).toFixed(0);
                progressElement.innerHTML = `${percentage}%`;
                progressElement.style = `width: ${percentage}%`

                // Update the percentage in the tab
                this.tabs[i].innerHTML = `Maturity Level ${i + 1} (${percentage}%)`
            }
        },
    };
});
