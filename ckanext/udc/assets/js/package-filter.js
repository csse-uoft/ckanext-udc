// For Package Search - Advanced Filter

this.ckan.module('filter-multiple-select', function ($) {
    return {
        options: {
            
        },
        initialize: function() {
            const fieldName = this.el[0].name;
            const data = [];
            const selected = [];

            for (const {name, display_name, active, count} of window.facets.data[fieldName]) {
                const item = {
                    id: encodeURIComponent(name), // prevent special characters that mess up select2
                    text: display_name + ` - (${count})`
                };
                data.push(item)
                if (active) {
                    selected.push(item);
                }
            }
        
            this.el.select2({multiple: true, width: 'resolve', data});
            this.el.select2('data', selected);
        }

    }
});

this.ckan.module('filter-apply-button', function($) {
    return {
        initialize: function () {
            this.el[0].onclick = () => {
                const url = window.location.pathname;
                const params = new Set();
                const usedNames = new Set();
                
                // Set filters that we selected in the popup
                for (const filteName in window.facets.titles) {
                    const el = $(`#filter-${filteName}`);
                    if (el) {
                        console.log(el)
                        usedNames.add(filteName);
                        const filterValues = el.select2('data').map(v => v.id);
                        for (const filterValue of filterValues) {
                            params.add(`${encodeURIComponent(filteName)}=${filterValue}`);
                        }
                    }
                }

                // Preserve the exising filters and deduplicate
                for (const [k, v] of new URLSearchParams(window.location.search).entries()) {
                    if (!usedNames.has(k))
                        params.add(`${encodeURIComponent(k)}=${encodeURIComponent(v)}`);
                }

                // Redirect
                window.location.href = "/dataset/?" + [...params].join('&');
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

