const urlParams = new Map(); // string -> string[]
const currURLSearchParams = new URLSearchParams(window.location.search);
for (const [k, v] of currURLSearchParams.entries()) {
    if (urlParams.has(k)) {
        urlParams.get(k).push(v);
    } else {
        urlParams.set(k, [v]);
    }
}

const AND_TEXT = "Match all selected (AND)";
const OR_TEXT = "Match any selected (OR)";

function multiSelectLabelRenderer(data) {
    if (data.isNew) {
        return `Search for "${data.label}"`;
    }
    return `${data.label}`;
}

const CKANFields = ["title", "notes", "url", "version",
    "author", "author_email", "maintainer", "maintainer_email"];

/**
 * For full text search, we add a prefix `fts_` to the field name.
 * For exact match search, we add a prefix `exact_` to the field name.
 * 
 * Only type=text fields are supported for full text search
 * 
 * filter-logic-<field_name> is used to determine if the filter logic is AND or OR.
 * 
 */
this.ckan.module('filter-multiple-select', function ($) {
    return {
        options: {
            filterToggle: false,
        },

        initialize: function () {
            const id = this.el[0].getAttribute("id");
            const fieldName = this.el[0].getAttribute("name");
            let facets;
            let useExtras = false;
            let allowNewOption = [...window.facets.textFields, ...CKANFields].includes(fieldName);


            if (window.facets.data["extras_" + fieldName]) {
                facets = window.facets.data["extras_" + fieldName];
                useExtras = true;
            } else {
                facets = window.facets.data[fieldName];
            }
           
            if (!facets) {
                console.warn(`No facets found for ${fieldName}`);
                // return;
            }
            // console.log(fieldName, this.options, this.el[0])

            if (this.options.filterToggle) {
                // Add a filter toggle button after this.el[0]
                const html = `
                    <div class="form-check form-switch mt-1">
                        <input class="form-check-input" type="checkbox" role="switch" id="${`filter-toggle-${fieldName}`}">
                        <label class="form-check-label" for="${`filter-toggle-${fieldName}`}" id="${`filter-toggle-label-${fieldName}`}">${OR_TEXT}</label>
                    </div>`.trim();
                this.el[0].parentElement.nextElementSibling.insertAdjacentHTML('afterend', html);
                
                // Check if the filter logic is set to "and"
                if (urlParams.has(`filter-logic-${fieldName}`) && urlParams.get(`filter-logic-${fieldName}`)[0] === "AND") {
                    document.getElementById(`filter-toggle-${fieldName}`).checked = true;
                    document.getElementById(`filter-toggle-label-${fieldName}`).textContent = AND_TEXT;
                }

                document.getElementById(`filter-toggle-${fieldName}`).addEventListener('change', function (e) {
                    const label = document.getElementById(`filter-toggle-label-${fieldName}`);
                    if (this.checked) {
                        label.textContent = AND_TEXT;
                    } else {
                        label.textContent = OR_TEXT;
                    }
                });
                
            }

            const data = [];
            const optionsKey = new Set();
            const selected = [];
            // console.log(fieldName, facets)
            for (const { name, display_name, active, count } of facets || []) {
                const item = {
                    value: encodeURIComponent(name), // Prevents special characters breaking Virtual Select
                    label: `${display_name} - (${count})`
                };
                data.push(item);
                optionsKey.add(item.value);
                if (active) {
                    selected.push(item.value);
                }
            }

            // Add fields that are not in facets (title, description, etc.)
            if (urlParams.has(`fts_${fieldName}`)) {
                for (const value of urlParams.get(`fts_${fieldName}`)) {
                    console.log("Adding fts_", fieldName, value);
                    let item = {
                        value: value,
                        label: value,
                        isNew: true,
                    };
                    
                    // Prevent duplicates
                    if (!optionsKey.has(item.value)) {
                        data.push(item);
                    }
                    selected.push(item.value);
                }
            }

            // Add fields beginning with `exact_`
            if (urlParams.has(`exact_${fieldName}`)) {
                for (const value of urlParams.get(`exact_${fieldName}`)) {
                    console.log("Adding exact_", fieldName, value);
                    const item = {
                        value: value,
                        label: value,
                    };

                    // Prevent duplicates
                    if (!optionsKey.has(item.value)) {
                        data.push(item);
                    }
                    selected.push(item.value);
                }
            }

            // https://sa-si-dev.github.io/virtual-select/#/properties
            const selectComponent = VirtualSelect.init({
                ele: this.el[0],
                options: data,
                multiple: true,
                search: true,
                selectedValue: selected,
                allowNewOption,
                maxWidth: "100%",
                showValueAsTags: true,
                disabled: false,
                labelRenderer: multiSelectLabelRenderer,
                selectedLabelRenderer: multiSelectLabelRenderer,
            });

        }
    }
});

this.ckan.module('filter-apply-button', function ($) {
    return {
        initialize: function () {
            this.el[0].onclick = () => {
                const url = window.location.pathname;
                const params = new Set();
                const usedNames = new Set();

                // Set filters that we selected in the dropdown
                for (let fieldName of [...Object.keys(window.facets.titles), ...CKANFields]) {
                    // Remove the "extras_" prefix if it exists
                    const useExtras = fieldName.startsWith("extras_");
                    if (useExtras) {
                        fieldName = fieldName.substring(7);
                    }
                    console.log("Field name", fieldName);
                    const el = document.querySelector(`#filter-${fieldName}`);
                    const filterToggle = document.getElementById(`filter-toggle-${fieldName}`);
                    if (el) {
                        usedNames.add(fieldName);
                        const filterValues = el.getSelectedOptions();
                        for (let { value, label, isNew } of filterValues) {

                            if (!CKANFields.includes(fieldName)) {
                                if (isNew) {
                                    params.add(`fts_${encodeURIComponent(fieldName)}=${value}`);
                                    console.log("Adding fts_", fieldName, value);
                                } else {
                                    params.add(`exact_${encodeURIComponent(fieldName)}=${value}`);
                                    console.log("Adding exact_", fieldName, value);
                                }
                            } 
                            if (CKANFields.includes(fieldName)) {
                                if (isNew) {
                                    params.add(`fts_${encodeURIComponent(fieldName)}=${value}`);
                                    console.log("Adding fts_", fieldName, value);
                                } else {
                                    params.add(`exact_${encodeURIComponent(fieldName)}=${value}`);
                                    console.log("Adding exact_", fieldName, value);
                                }
                            }
                        }
                        if (filterToggle && filterToggle.checked) {
                            params.add(`filter-logic-${fieldName}=AND`);
                        }
                    }
                }
                
                // Preserve existing filters and deduplicate
                console.log(currURLSearchParams.entries())
                for (const [k, v] of currURLSearchParams.entries()) {
                    // Add those params that are not covered by the usedNames
                    if (k.startsWith("exact_")) {
                        // Remove the "exact_" prefix
                        if (!usedNames.has(k.substring(7))) {
                            params.add(`${k}=${v}`);
                        }
                    } else if (k.startsWith("fts_")) {
                        // Remove the "fts_" prefix
                        if (!usedNames.has(k.substring(4))) {
                            params.add(`${k}=${v}`);
                        }
                    } else if (!usedNames.has(k)) {
                        params.add(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
                    }
                  
                }

                // Redirect
                window.location.href = window.facets.bsaeURL + "?" + [...params].join('&');
            };
        }
    }
});

// Initialize Bootstrap Tooltips
window.onload = function () {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));
};
