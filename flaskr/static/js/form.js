function validateForm() {
    const loginForm = document.forms['login'];
    const emailInput = loginForm['email'].value;
    const passwordInput = loginForm['password'].value;
    const submitButton = loginForm.querySelector('input[type="submit"]');

    if (emailInput && passwordInput) {
        submitButton.disabled = false;
        console.log('Enabling')
    } else {
        submitButton.disabled = true
        console.log('Disabling')
    }
}