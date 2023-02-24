/**
 * UDC Customized Package Form.
 * Sync CKAN fields with the UDC fields.
 */
this.ckan.module('package-form', function ($) {
    return {
        initialize: function () {
            this.clonedFields = [];

            // Percentages on each maturity level
            this.levels = []; // number of fields in each level
            for (const [i, level] of window.packageConfig.entries()) {
                if (level.fields) {
                    this.levels[i] = {
                        totalFields: level.fields.length,
                        fieldElements: [],
                        progressElement: document.querySelector('#progress-' + (i + 1))
                    }

                    for (const field of level.fields) {
                        if (field.name) {
                            const fieldElement = document.querySelector(`#field-${field.name}`);
                            fieldElement.addEventListener('change', () => this._onFieldChange());
                            this.levels[i].fieldElements.push(fieldElement);
                        } else if (field.ckanField) {
                            const fieldId = `field-${field.ckanField}-clone`;
                            this.clonedFields.push(fieldId);
                            const fieldElement = document.querySelector(`#${fieldId}`);
                            this.levels[i].fieldElements.push(fieldElement);
                        }
                    }
                }
            }
            
            // Sync UDC fields with CKAN fields
            const syncedFields = document.querySelectorAll("[sync-with]");
            for (const syncedField of syncedFields) {
                const targetElementId = syncedField.getAttribute('sync-with');
                const targetElement = document.querySelector(`#${targetElementId}`);
                
                if (targetElementId === 'field-title') {
                    // We also need to sync the input to URL
                    const urlElement = document.querySelector("#field-name");

                    syncedField.addEventListener('change', (e) => {
                        if (targetElement) targetElement.value = e.target.value;
                        if (urlElement) urlElement.value = e.target.value;

                        // The preview is generated after this script is loaded.
                        document.querySelector(".slug-preview-value").innerHTML = e.target.value;
                        this._onFieldChange();
                        e.stopPropagation();
                    });
                    targetElement.addEventListener('change', (e) => {
                        syncedField.value = e.target.value;
                        this._onFieldChange();
                        e.stopPropagation();
                    });
                } else if (targetElement.getAttribute('data-module') === 'autocomplete') {
                    // Special case for autocomplete that uses 'select2'
                    // See https://select2.github.io/select2/#documentation
                    const targetSelect = $(`#${targetElementId}`);
                    const syncedSelect = $(`#${syncedField.id}`);
                    targetSelect.on('change', e => {
                        syncedSelect.select2('data', targetSelect.select2('data'));
                        this._onFieldChange();
                    });
                    syncedSelect.on('change', e => {
                        targetSelect.select2('data', syncedSelect.select2('data'));
                        this._onFieldChange();
                    });
                   
                } else {
                    syncedField.addEventListener('change', (e) => {
                        targetElement.value = e.target.value;                        
                        this._onFieldChange();
                        e.stopPropagation();
                    });
                    targetElement.addEventListener('change', (e) => {
                        syncedField.value = e.target.value;
                        this._onFieldChange();
                        e.stopPropagation();
                    });
                }

               
            }

            // Add evenet listener for the "Next: Add Data button"
            this.form = document.querySelector('form#dataset-edit');
            const button = document.querySelector('button[type="submit"].btn-primary');
            button.addEventListener('click', () => {
                this._onClick();
            });

            // Trigger _onFieldChange to set percentage
            this._onFieldChange();

        },
        _onFieldChange: function() {
            console.log('updated')
            // Calculate percentage after field changed
            for (const {totalFields, fieldElements, progressElement} of this.levels) {
                let inputtedFields = 0;
                for (const fieldElement of fieldElements) {
                    if (fieldElement.value != null && fieldElement.value !== '') {
                        inputtedFields++;
                    }
                }
                // Update the percentage bar
                const percentage = (inputtedFields / totalFields * 100).toFixed(0);
                progressElement.innerHTML = `${percentage}%`;
                progressElement.style = `width: ${percentage}%`
            }
        },
        _onClick: function () {
            // Remove the #***-clone inputs
            for (const fieldName of this.clonedFields) {
                this.form[fieldName].value = undefined;
            }
        }
    };
});
