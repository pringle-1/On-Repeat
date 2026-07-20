function showPassword(id) {
    document.getElementById(id).type = "text";
}

function hidePassword(id) {
    document.getElementById(id).type = "password";
}

function togglePassword(id) {
    const password = document.getElementById(id);

    if (password.type === "password") {
        password.type = "text";
    } else {
        password.type = "password";
    }
}