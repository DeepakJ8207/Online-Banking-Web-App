/**
 * PRIME RESERVE BANK - Core JavaScript Helpers & Loading States
 */

// 1. Robust Password Visibility Toggle Helper
window.togglePasswordVisibility = function(targetId, btnEl) {
    let inputField = null;
    if (targetId) {
        inputField = document.getElementById(targetId);
    }
    if (!inputField && btnEl) {
        inputField = btnEl.closest('.input-group')?.querySelector('input') || btnEl.previousElementSibling;
    }
    if (inputField) {
        const icon = btnEl ? (btnEl.querySelector('i') || btnEl) : null;
        if (inputField.type === 'password') {
            inputField.type = 'text';
            if (icon) {
                icon.classList.remove('bi-eye');
                icon.classList.add('bi-eye-slash');
            }
        } else {
            inputField.type = 'password';
            if (icon) {
                icon.classList.remove('bi-eye-slash');
                icon.classList.add('bi-eye');
            }
        }
    }
};

// Global click event delegation for any toggle-password-btn
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.toggle-password-btn');
    if (btn) {
        e.preventDefault();
        e.stopPropagation();
        const targetId = btn.getAttribute('data-target');
        window.togglePasswordVisibility(targetId, btn);
    }
});

document.addEventListener('DOMContentLoaded', function() {

    // 2. Copy To Clipboard Helper
    window.copyToClipboard = function(text, label = 'Copied to clipboard!') {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                showToast(label, 'success');
            }).catch(err => {
                fallbackCopyTextToClipboard(text, label);
            });
        } else {
            fallbackCopyTextToClipboard(text, label);
        }
    };

    function fallbackCopyTextToClipboard(text, label) {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {
            document.execCommand('copy');
            showToast(label, 'success');
        } catch (err) {
            showToast('Unable to copy', 'error');
        }
        document.body.removeChild(textArea);
    }

    // 3. Simple Toast Trigger
    window.showToast = function(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;

        const toastEl = document.createElement('div');
        const bgClass = type === 'success' ? 'bg-success text-white' : (type === 'error' ? 'bg-danger text-white' : 'bg-dark text-white');
        
        toastEl.className = `toast align-items-center ${bgClass} border-0 show shadow-lg mb-2`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');

        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body py-2 px-3 fw-medium">
                    <i class="bi ${type === 'success' ? 'bi-check-circle-fill' : (type === 'error' ? 'bi-exclamation-triangle-fill' : 'bi-info-circle-fill')} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;

        toastContainer.appendChild(toastEl);
        setTimeout(() => {
            toastEl.classList.remove('show');
            setTimeout(() => toastEl.remove(), 300);
        }, 3500);
    };

    // 4. Autofill Demo Credentials (On Login Page)
    window.fillDemoCredentials = function(username, password) {
        const userInput = document.getElementById('login-username');
        const pwdInput = document.getElementById('login-password');
        if (userInput && pwdInput) {
            userInput.value = username;
            pwdInput.value = password;
            showToast(`Loaded ${username} credentials!`, 'success');
        }
    };

    // 5. One-Click Instant Auto Login Helper
    window.loginDirectly = function(username, password) {
        const userInput = document.getElementById('login-username');
        const pwdInput = document.getElementById('login-password');
        const form = userInput ? userInput.closest('form') : null;
        if (userInput && pwdInput && form) {
            userInput.value = username;
            pwdInput.value = password;
            
            // Add visual loading state
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Authenticating...';
            }
            form.submit();
        }
    };

    // 6. Form Submit Button Loading State Handler
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.hasAttribute('data-no-spinner')) {
                setTimeout(() => {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Processing...';
                }, 50);
            }
        });
    });
});
