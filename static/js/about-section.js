// About Section Functionality
function showAboutSection() {
    const aboutSection = document.getElementById('about-us');
    if (aboutSection) {
        aboutSection.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }
}

function hideAboutSection() {
    const aboutSection = document.getElementById('about-us');
    if (aboutSection) {
        aboutSection.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
    }
}

// Close about section when clicking outside content
document.addEventListener('DOMContentLoaded', () => {
    const aboutSection = document.getElementById('about-us');
    if (aboutSection) {
        aboutSection.addEventListener('click', (e) => {
            if (e.target === aboutSection) {
                hideAboutSection();
            }
        });
    }

    // Handle escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideAboutSection();
        }
    });

    // Custom Cursor functionality
    const customCursor = document.querySelector('.custom-cursor');
    const interactiveElements = 'a, button, input[type="submit"], input[type="button"], input[type="text"], input[type="email"], input[type="password"], textarea';

    // Move the custom cursor with the mouse
    document.addEventListener('mousemove', (e) => {
        if (customCursor) {
            customCursor.style.left = `${e.clientX}px`;
            customCursor.style.top = `${e.clientY}px`;
        }
    });

    // Add hover effect for interactive elements
    document.querySelectorAll(interactiveElements).forEach(element => {
        element.addEventListener('mouseenter', () => {
            if (customCursor) {
                customCursor.classList.add('hovered');
            }
        });
        element.addEventListener('mouseleave', () => {
            if (customCursor) {
                customCursor.classList.remove('hovered');
            }
        });
    });

    // Smooth scrolling for sidebar links and active state management
    const sidebarLinks = document.querySelectorAll('.about-sidebar .sidebar-link');
    const sections = document.querySelectorAll('.about-section-content');

    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);

            if (targetSection) {
                window.scrollTo({
                    top: targetSection.offsetTop - 70, // Adjust for fixed header/navbar
                    behavior: 'smooth'
                });

                // Update active class immediately on click
                sidebarLinks.forEach(item => item.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });

    // Observe sections for active link highlighting during scroll
    const observerOptions = {
        root: null,
        rootMargin: '-50% 0px -50% 0px', // Adjust this to control when the section becomes active
        threshold: 0
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const currentActive = document.querySelector('.about-sidebar .sidebar-link.active');
                if (currentActive) {
                    currentActive.classList.remove('active');
                }
                const correspondingLink = document.querySelector(`.about-sidebar .sidebar-link[href="#${entry.target.id}"]`);
                if (correspondingLink) {
                    correspondingLink.classList.add('active');
                }
            }
        });
    }, observerOptions);

    sections.forEach(section => {
        observer.observe(section);
    });
}); 