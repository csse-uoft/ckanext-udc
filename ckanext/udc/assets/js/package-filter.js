// For Package Search - Advanced Filter

const urlParams = new Map(); // string -> string[]
const currURLSearchParams = new URLSearchParams(window.location.search);
for (const [k, v] of currURLSearchParams.entries()) {
    if (urlParams.has(k)) {
        urlParams.get(k).push(v);
    } else {
        urlParams.set(k, [v]);
    }
}

const FUZZY_PREFIX = "__fuzzy_";

this.ckan.module('filter-multiple-select', function ($) {
    return {
        options: {

        },
        initialize: function () {
            const fieldName = this.el[0].name;
            const data = [];
            const selected = [];

            for (const { name, display_name, active, count } of window.facets.data[fieldName] || []) {
                const item = {
                    id: encodeURIComponent(name), // prevent special characters that mess up select2
                    text: display_name + ` - (${count})`
                };
                data.push(item)
                if (active) {
                    selected.push(item);
                }
            }
            // Add fields that are not in facets (title, description, ...)
            if (data.length === 0 && !window.facets.data[fieldName] && urlParams.has(fieldName)) {
                for (const value of urlParams.get(fieldName)) {
                    const item = {
                        id: value,
                        text: `Search for "${value}"`,
                    };
                    data.push(item);
                    selected.push(item);
                }
            }
            // Add fields begin with `extras_`
            if (urlParams.has(`extras_${fieldName}`)) {
                for (const value of urlParams.get(`extras_${fieldName}`)) {
                    const item = {
                        id: FUZZY_PREFIX + value,
                        text: `Search for "${value}"`,
                    };
                    data.push(item);
                    selected.push(item);
                }
            }

            this.el.select2({
                multiple: true, width: 'resolve', data,
                createSearchChoice: function (term, data) {
                    if ($(data).filter(function () { return this.text.localeCompare(term) === 0; }).length === 0) {
                        return { id: FUZZY_PREFIX + term, text: `Search for "${term}"` };
                    }
                }
            });
            this.el.select2('data', selected);
        }

    }
});

this.ckan.module('filter-apply-button', function ($) {
    // The fields that are always use fuzzy search
    const CKANFields = ["title", "notes", "source", "version",
        "author", "author_email", "maintainer", "maintainer_email"]
    return {
        initialize: function () {
            this.el[0].onclick = () => {
                const url = window.location.pathname;
                const params = new Set();
                const usedNames = new Set();

                // Set filters that we selected in the popup
                for (const filteName of [...Object.keys(window.facets.titles), ...CKANFields]) {
                    const el = $(`#filter-${filteName}`);
                    if (el) {
                        // console.log(el)
                        usedNames.add(filteName);
                        const filterValues = el.select2('data').map(v => v.id);
                        for (let filterValue of filterValues) {
                            const isFuzzy = filterValue.startsWith(FUZZY_PREFIX);
                            if (isFuzzy) {
                                filterValue = filterValue.slice(FUZZY_PREFIX.length);
                            }

                            if (!CKANFields.includes(filteName) && isFuzzy) {
                                params.add(`extras_${encodeURIComponent(filteName)}=${filterValue}`);
                            } else {
                                params.add(`${encodeURIComponent(filteName)}=${filterValue}`);
                            }
                        }
                    }
                }

                // Preserve the exising filters and deduplicate
                for (const [k, v] of new URLSearchParams(window.location.search).entries()) {
                    if (!usedNames.has(k))
                        params.add(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
                }
                // Redirect
                window.location.href = "/catalogue/?" + [...params].join('&');
            }
        }
    }
});


window.onload = function () {
    // Initialize Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

}

