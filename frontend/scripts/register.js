/**
 * Registration form formatting, validation, and submission handler
 */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("register-form");
  const cpfInput = document.getElementById("cpf");
  const phoneInput = document.getElementById("phone");

  // Format CPF as 000.000.000-00
  cpfInput.addEventListener("input", (event) => {
    let value = event.target.value.replace(/\D/g, "").slice(0, 11);
    value = value.replace(/(\d{3})(\d)/, "$1.$2");
    value = value.replace(/(\d{3})(\d)/, "$1.$2");
    value = value.replace(/(\d{3})(\d{1,2})$/, "$1-$2");
    event.target.value = value;
  });

  // Format Phone as (00) 00000-0000
  phoneInput.addEventListener("input", (event) => {
    let value = event.target.value.replace(/\D/g, "").slice(0, 11);
    if (value.length > 2) {
      value = `(${value.slice(0, 2)}) ${value.slice(2)}`;
    }
    if (value.length > 10) {
      value = `${value.slice(0, 10)}-${value.slice(10)}`;
    }
    event.target.value = value;
  });

  // Helper to toggle field error state
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

  // Validate form fields before submission
  const validateForm = () => {
    let isValid = true;

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;
    const cpfDigits = cpfInput.value.replace(/\D/g, "");
    const birthDate = document.getElementById("birth-date").value;
    const address = document.getElementById("address").value.trim();

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setFieldError("email", "email-error", "Informe um endereço de e-mail válido.");
      isValid = false;
    } else {
      setFieldError("email", "email-error", "");
    }

    // Password validation
    if (password.length < 6) {
      setFieldError("password", "password-error", "A senha deve ter pelo menos 6 caracteres.");
      isValid = false;
    } else {
      setFieldError("password", "password-error", "");
    }

    // CPF length validation
    if (cpfDigits.length !== 11) {
      setFieldError("cpf", "cpf-error", "Informe um CPF válido com 11 dígitos.");
      isValid = false;
    } else {
      setFieldError("cpf", "cpf-error", "");
    }

    // Birth date validation
    if (!birthDate) {
      setFieldError("birth-date", "birth-date-error", "Informe sua data de nascimento.");
      isValid = false;
    } else {
      setFieldError("birth-date", "birth-date-error", "");
    }

    // Address validation
    if (address.length < 5) {
      setFieldError("address", "address-error", "Informe seu endereço completo.");
      isValid = false;
    } else {
      setFieldError("address", "address-error", "");
    }

    return isValid;
  };

  // Handle form submission
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    // Payload structured to match the backend BaseModel schemas / database 'account' table
    const accountPayload = {
      email: document.getElementById("email").value.trim(),
      password: document.getElementById("password").value,
      cpf: cpfInput.value.replace(/\D/g, ""),
      birth_date: document.getElementById("birth-date").value,
      phone: phoneInput.value.replace(/\D/g, "") || null,
      address: document.getElementById("address").value.trim()
    };

    const submitButton = form.querySelector("button[type='submit']");
    
    try {
      if (submitButton) submitButton.disabled = true;

      // Send data to FastAPI backend endpoint
      const response = await fetch("http://localhost:8000/api/accounts/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(accountPayload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = errorData?.detail;
        const fallback = "Erro ao realizar o cadastro. Verifique os dados inseridos.";
        const fieldLabels = {
          email: "E-mail", password: "Senha", cpf: "CPF",
          birth_date: "Data de nascimento", phone: "Telefone", address: "Endereço"
        };
        // FastAPI validation errors contain a list of objects, not a string.
        const messages = Array.isArray(detail) ? detail
          .filter(item => item && typeof item.msg === "string")
          .map(item => {
            const field = Array.isArray(item.loc) ? item.loc[1] : null;
            const label = fieldLabels[field];
            return label ? `${label}: ${item.msg}` : item.msg;
          }) : [];
        const message = typeof detail === "string" && detail.trim()
          ? detail : messages.join("\n") || fallback;
        throw new Error(message);
      }

      const result = await response.json();

      // Store account ID in sessionStorage for the next step (plans)
      sessionStorage.setItem("quaseflix_account_id", result.id);

      // Proceed to plan selection page
      window.location.href = "./plans.html";

    } catch (error) {
      console.error("Registration error:", error);
      alert(error.message || "Não foi possível conectar ao servidor.");
      if (submitButton) submitButton.disabled = false;
    }
  });
});
