/**
 * Global Compass Navigation Handler
 * Handles click events for all compass navigation buttons
 */

document.addEventListener('DOMContentLoaded', function() {
    // Find compass nav element
    const compass = document.getElementById('compassNav') || document.querySelector('.compass-nav');
    
    if (!compass) {
        console.log('No compass navigation found on this page');
        return;
    }
    
    // Add click handler to toggle
    compass.addEventListener('click', function(event) {
        // Don't trigger if clicking on a link inside menu
        if (event.target.closest('.compass-item')) {
            return;
        }
        
        event.stopPropagation();
        this.classList.toggle('active');
    });
    
    // Stop propagation on menu clicks
    const menu = compass.querySelector('.compass-menu');
    if (menu) {
        menu.addEventListener('click', function(event) {
            event.stopPropagation();
        });
    }
    
    // Close compass when clicking outside
    document.addEventListener('click', function(event) {
        if (!compass.contains(event.target)) {
            compass.classList.remove('active');
        }
    });
    
    // Close compass on ESC key
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            compass.classList.remove('active');
        }
    });
});
