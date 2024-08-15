/**
 * UDC Customized Package View Page.
 */

function getPackageIdFromUrl(url) {
    const urlParts = url.split('/');
    return urlParts[urlParts.length - 1]; // The last part of the URL is the package ID
}

function loadPackageRelationships(packageId) {
    const url = `/api/3/action/package_relationships_list?id=${packageId}`;

    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const container = document.getElementById('unified-show-packages');
                container.innerHTML = ''; // Clear existing content

                // Create and append each link with an icon
                data.result.forEach(item => {
                    const link = document.createElement('a');
                    link.href = `/catalogue/${item.object}`;
                    link.title = item.object;
                    link.target = '_blank'; // Open in new tab
                    link.classList.add('d-flex', 'align-items-center', 'mb-2');

                    const icon = document.createElement('i');
                    icon.className = 'fas fa-box-open me-2'; // Font Awesome icon class with margin

                    const text = document.createElement('span');
                    text.textContent = item.object;

                    link.appendChild(icon);
                    link.appendChild(text);
                    container.appendChild(link);
                });
            } else {
                console.error('API response was not successful');
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
        });
}

window.onload = function () {
    // Initialize Tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Load unified package
    if (document.getElementById('unified-show-packages')) {
        const currentUrl = window.location.href;
        const packageId = getPackageIdFromUrl(currentUrl);
        loadPackageRelationships(packageId);
    }

}
