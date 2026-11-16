/**
 * Login form validation and submission handler
 */
document.addEventListener("DOMContentLoaded", () => {
  const API_BASE_URL = "http://localhost:8000";

  // Catalog access uses the authenticated account until Module 3 adds profiles.
  const POST_LOGIN_URL = "./catalog.html";

  // What the user reads for each HTTP status the login endpoint can answer with.
  const LOGIN_ERROR_MESSAGES = {
    401: "E-mail ou senha incorretos.",
    402: "Seu período de teste terminou e não há uma assinatura ativa. Regularize o pagamento para voltar a assistir.",
    403: "Esta conta foi cancelada e não pode ser acessada."
  };
  const GENERIC_ERROR_MESSAGE = "Não foi possível entrar. Tente novamente em instantes.";
  const CONNECTION_ERROR_MESSAGE = "Não foi possível conectar ao servidor.";

  const form = document.getElementById("login-form");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const formError = document.getElementById("login-error");
  const submitButton = form.querySelector("button[type='submit']");

  // Helper to toggle field error state (same behavior as register.js)
  const setFieldError = (inputId, errorId, message) => {
    const input = document.getElementById(inputId);
    const errorSpan = document.getElementById(errorId);
    if (message) {
      input.classList.add("input-error");
      errorSpan.textContent = message;
    } else {
      input.classList.remove("input-error");
      errorSpan.textContent = "";
    }
  };

  // Error that belongs to the whole form, shown above the fields
  const showFormError = (message) => {
    formError.textContent = message;
    formError.hidden = !message;
  };

  // The server decides if the credentials are right; this only avoids sending an empty form.
  const validateForm = () => {
    let isValid = true;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailInput.value.trim())) {
      setFieldError("email", "email-error", "Informe um endereço de e-mail válido.");
      isValid = false;
    } else {
      setFieldError("email", "email-error", "");
    }

    if (passwordInput.value.length === 0) {
      setFieldError("password", "password-error", "Informe a sua senha.");
      isValid = false;
    } else {
      setFieldError("password", "password-error", "");
    }

    return isValid;
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    showFormError("");

    if (!validateForm()) {
      return;
    }

    try {
      submitButton.disabled = true;

      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          email: emailInput.value.trim(),
          password: passwordInput.value
        })
      });

      if (!response.ok) {
        showFormError(LOGIN_ERROR_MESSAGES[response.status] || GENERIC_ERROR_MESSAGE);
        if (response.status === 401) {
          passwordInput.value = "";
          passwordInput.focus();
        }
        submitButton.disabled = false;
        return;
      }

      const result = await response.json();
      QuaseflixSession.save(result.token, result.account);
      window.location.href = POST_LOGIN_URL;

    } catch (error) {
      console.error("Login error:", error);
      showFormError(CONNECTION_ERROR_MESSAGE);
      submitButton.disabled = false;
    }
  });
});
