document.addEventListener('DOMContentLoaded', function() {
  var dropdowns = document.querySelectorAll('.nav .dropdown');

  // Ensure click behavior works on mobile
  dropdowns.forEach(function(dropdown) {
    dropdown.querySelector('.dropdown-toggle').addEventListener('click', function(e) {
      if (window.innerWidth < 992) {
        e.preventDefault(); // Prevent default anchor behavior on mobile devices
        var bsDropdown = new bootstrap.Dropdown(this);
        bsDropdown.toggle(); // Toggle the dropdown on click for mobile
      }
    });
  });

});
