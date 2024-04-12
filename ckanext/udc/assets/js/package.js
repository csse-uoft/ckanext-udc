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
            });

            // Initialize License dropdown
            const packageLicenses = window.packageLicenses;
            const licenseOptions = packageLicenses.map(l => ({
                label: `<div>${l[1]}${l[2] ? `<a class="ms-1" style="font-size:12px;vertical-align: text-bottom;" href="${l[2]}" target="_blank"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>` : ''}</div>`,
                value: l[0],
            }));
            console.log(licenseOptions)

            const licenseSelectedValue = document.querySelector('#field-license_id').getAttribute('value') || "";
            VirtualSelect.init({
                ele: `#field-license_id`,
                search: true,
                multiple: false,
                maxWidth: "100%",
                placeholder: 'Please select the license',
                options: licenseOptions,
                selectedValue: licenseSelectedValue,
                hasOptionDescription: false,
                optionsCount: 6,
                optionHeight: '40px'
            });
            const license_field = document.querySelector('#field-license_id');


            // Initialize Adding Custom Licenses
            const addLicenseBtn = document.querySelector("#add-license-popover-btn");
            const addLicenseContainer = document.querySelector(".add-license-container");
            addLicenseBtn.addEventListener('click', () => {
                if (addLicenseContainer.classList.contains("visible")) {
                    addLicenseContainer.classList.remove("visible");
                    addLicenseContainer.classList.add("hidden");
                } else {
                    addLicenseContainer.classList.remove("hidden");
                    addLicenseContainer.classList.add("visible");
                }
            });

            const newLicenseForm = document.getElementById("create-license-form");
            newLicenseForm.onsubmit = async function (e) {
                e.preventDefault();

                const api = document.getElementById("license-create-api").value;
                const formData = new FormData(newLicenseForm);
                const resp = await fetch(api, {
                    method: "POST",
                    body: formData
                });

                const errorBox = document.getElementById("new-license-error");
                const succssBox = document.getElementById("new-license-success");

                if (resp.status >= 400) {
                    const err = await resp.json();
                    if (err && err.error && err.error.message) {
                        errorBox.innerHTML = `<i class="fa-solid fa-circle-exclamation" style="padding-right:5px"></i>` + `<span>${err.error.message}</span>`;
                        errorBox.classList.remove('d-none');
                        succssBox.classList.add('d-none');
                    }
                } else {
                    // Success
                    // Add the option and select
                    license_field.addOption({
                        value: formData.get('id'),
                        label: formData.get('title'),
                    });
                    license_field.setValue(formData.get('id'));

                    errorBox.innerHTML = '';
                    errorBox.classList.add('d-none');
                    succssBox.classList.remove('d-none');
                }
            }

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

                            // setup multiple select
                            if (field.type === "multiple_select") {
                                const options = [];
                                const selectedOptions = [];
                                const curr_str = fieldElement.getAttribute('value') || "";
                                const curr = curr_str.split(",");

                                for (const option of field.options) {
                                    const selectOption = {
                                        value: option.value,
                                        label: option.text
                                    }
                                    options.push(selectOption);
                                    if (curr.includes(option.value)) {
                                        selectedOptions.push(selectOption.value);
                                    }
                                }

                                // https://sa-si-dev.github.io/virtual-select/#/properties
                                VirtualSelect.init({
                                    ele: `#field-${field.name}`,
                                    options,
                                    search: true,
                                    multiple: true,
                                    showValueAsTags: true,
                                    selectedValue: selectedOptions,
                                    maxWidth: "100%",
                                    allowNewOption: field.allowNewOption,
                                })

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
        _onFieldChange: function () {
            // console.log('updated')
            // Calculate percentage after field changed
            for (const [i, { fieldElements, progressElement }] of this.levels.entries()) {
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
