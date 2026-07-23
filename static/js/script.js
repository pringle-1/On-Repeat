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

document.addEventListener("mouseup", hidePassword);
document.addEventListener("touchend", hidePassword);