// Analytics UI/UX Enhancements
document.addEventListener('DOMContentLoaded', function() {
    
    // Smooth scroll for navigation
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add ripple effect to buttons
    function createRipple(event) {
        const button = event.currentTarget;
        const circle = document.createElement("span");
        const diameter = Math.max(button.clientWidth, button.clientHeight);
        const radius = diameter / 2;
        
        circle.style.width = circle.style.height = `${diameter}px`;
        circle.style.left = `${event.clientX - button.offsetLeft - radius}px`;
        circle.style.top = `${event.clientY - button.offsetTop - radius}px`;
        circle.classList.add("ripple");
        
        const ripple = button.getElementsByClassName("ripple")[0];
        if (ripple) {
            ripple.remove();
        }
        
        button.appendChild(circle);
    }
    
    // Apply ripple to all buttons
    const buttons = document.querySelectorAll('.filter-btn, .chart-action-btn, .nav-pill');
    buttons.forEach(button => {
        button.addEventListener('click', createRipple);
    });
    
    // Animate cards on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-up');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe all cards
    document.querySelectorAll('.stat-card, .chart-card, .table-card').forEach(card => {
        observer.observe(card);
    });
    
    // Removed parallax effect to keep header fixed
    
    // Add number animation to stat values
    function animateValue(element, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const value = Math.floor(progress * (end - start) + start);
            element.textContent = value.toLocaleString();
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }
    
    // Animate stat values when they come into view
    const statObserver = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const endValue = parseInt(element.getAttribute('data-value') || element.textContent.replace(/\D/g, ''));
                if (!isNaN(endValue)) {
                    animateValue(element, 0, endValue, 1500);
                }
                statObserver.unobserve(element);
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.stat-value').forEach(stat => {
        statObserver.observe(stat);
    });
    
    // Enhanced filter interactions
    const filterInputs = document.querySelectorAll('.filter-input');
    filterInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('filter-group-active');
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('filter-group-active');
        });
    });
    
    // Add floating labels to filter inputs
    filterInputs.forEach(input => {
        if (input.value) {
            input.parentElement.classList.add('has-value');
        }
        
        input.addEventListener('input', function() {
            if (this.value) {
                this.parentElement.classList.add('has-value');
            } else {
                this.parentElement.classList.remove('has-value');
            }
        });
    });
    
    // Create animated background particles
    function createParticles() {
        const particlesContainer = document.createElement('div');
        particlesContainer.className = 'particles-container';
        document.body.appendChild(particlesContainer);
        
        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('div');
            particle.className = 'floating-particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 20 + 's';
            particle.style.animationDuration = (20 + Math.random() * 20) + 's';
            particlesContainer.appendChild(particle);
        }
    }
    
    // Initialize particles
    if (!document.querySelector('.particles-container')) {
        createParticles();
    }
    
    // Add keyboard navigation
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            // Close any open modals or dropdowns
            document.querySelectorAll('.modal-open').forEach(modal => {
                modal.classList.remove('modal-open');
            });
        }
    });
    
    // Enhanced chart interactions
    document.querySelectorAll('.chart-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Add loading states
    window.addEventListener('beforeunload', function() {
        document.body.classList.add('page-loading');
    });
    
    // Remove loading state when page is ready
    window.addEventListener('load', function() {
        document.body.classList.remove('page-loading');
    });
});

// Add necessary CSS for animations
const style = document.createElement('style');
style.textContent = `
    .ripple {
        position: absolute;
        border-radius: 50%;
        transform: scale(0);
        animation: ripple 600ms linear;
        background-color: rgba(255, 255, 255, 0.7);
    }
    
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .fade-in-up {
        animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .particles-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 0;
        overflow: hidden;
    }
    
    .floating-particle {
        position: absolute;
        width: 4px;
        height: 4px;
        background: linear-gradient(135deg, #667eea, #764ba2);
        border-radius: 50%;
        opacity: 0.3;
        animation: float-up 20s linear infinite;
    }
    
    @keyframes float-up {
        from {
            transform: translateY(100vh) translateX(0);
            opacity: 0;
        }
        10% {
            opacity: 0.3;
        }
        90% {
            opacity: 0.3;
        }
        to {
            transform: translateY(-100vh) translateX(100px);
            opacity: 0;
        }
    }
    
    .filter-group-active .filter-label {
        color: #667eea;
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    
    .page-loading {
        cursor: wait;
    }
    
    .page-loading * {
        pointer-events: none !important;
    }
`;
document.head.appendChild(style);