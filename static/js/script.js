let currentPassword = null;

function showPassword(id) {
    currentPassword = document.getElementById(id);

    if (currentPassword) {
        currentPassword.type = "text";
    }
}

function hidePassword() {
    if (currentPassword) {
        currentPassword.type = "password";
        currentPassword = null;
    }
}

function toggleEye() {
    const password = document.getElementById("password");
    const eye = document.getElementById("password-button");

    if (password.value.length > 0) {
        eye.style.display = "block";
    } else {
        eye.style.display = "none";
        hidePassword();
    }
}

document.addEventListener("mouseup", hidePassword);
document.addEventListener("touchend", hidePassword);