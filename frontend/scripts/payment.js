/**
 * Payment method form: field formatting, validation and submission handler
 */
document.addEventListener("DOMContentLoaded", () => {
  const API_BASE_URL = "http://localhost:8000";

  // The account id is saved by register.js right after the account is created.
  const accountId = sessionStorage.getItem("quaseflix_account_id");
  if (!accountId) {
    window.location.href = "./register.html";
    return;
  }

  const form = document.getElementById("payment-form");
  const typeRadios = form.querySelectorAll("input[name='payment-type']");
  const cardFields = document.getElementById("credit-card-fields");
  const boletoInfo = document.getElementById("boleto-info");
  const cardNumberInput = document.getElementById("card-number");
  const holderNameInput = document.getElementById("holder-name");
  const expiryInput = document.getElementById("expiry");
  const cvcInput = document.getElementById("cvc");
  const bankNameInput = document.getElementById("bank-name");
  const successBox = document.getElementById("payment-success");
  const successText = document.getElementById("payment-success-text");

  const getSelectedType = () => form.querySelector("input[name='payment-type']:checked").value;

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

  const clearCardErrors = () => {
    setFieldError("card-number", "card-number-error", "");
    setFieldError("holder-name", "holder-name-error", "");
    setFieldError("expiry", "expiry-error", "");
    setFieldError("cvc", "cvc-error", "");
  };

  // Show only the fields of the selected payment type
  const updateVisibleFields = () => {
    const isCard = getSelectedType() === "credit_card";
    cardFields.hidden = !isCard;
    boletoInfo.hidden = isCard;
    if (!isCard) {
      clearCardErrors();
    }
  };

  typeRadios.forEach((radio) => radio.addEventListener("change", updateVisibleFields));

  // Format card number as 0000 0000 0000 0000
  cardNumberInput.addEventListener("input", (event) => {
    const digits = event.target.value.replace(/\D/g, "").slice(0, 19);
    event.target.value = digits.replace(/(\d{4})(?=\d)/g, "$1 ");
  });

  // Format expiry as MM/AA
  expiryInput.addEventListener("input", (event) => {
    let value = event.target.value.replace(/\D/g, "").slice(0, 4);
    if (value.length > 2) {
      value = `${value.slice(0, 2)}/${value.slice(2)}`;
    }
    event.target.value = value;
  });

  // CVC accepts digits only
  cvcInput.addEventListener("input", (event) => {
    event.target.value = event.target.value.replace(/\D/g, "").slice(0, 4);
  });

  // Luhn checksum: catches most typos before calling the server
  const passesLuhn = (digits) => {
    let sum = 0;
    for (let i = 0; i < digits.length; i++) {
      let digit = Number(digits[digits.length - 1 - i]);
      if (i % 2 === 1) {
        digit *= 2;
        if (digit > 9) digit -= 9;
      }
      sum += digit;
    }
    return sum % 10 === 0;
  };

  // "MM/AA" -> { month, year } or null
  const parseExpiry = (value) => {
    const match = /^(\d{2})\/(\d{2})$/.exec(value);
    if (!match) return null;
    const month = Number(match[1]);
    if (month < 1 || month > 12) return null;
    return { month, year: 2000 + Number(match[2]) };
  };

  const isExpired = ({ month, year }) => {
    const now = new Date();
    return year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1);
  };

  // The server validates everything again; this is only for quick feedback.
  const validateCardFields = () => {
    let isValid = true;

    const cardDigits = cardNumberInput.value.replace(/\D/g, "");
    if (cardDigits.length < 13 || cardDigits.length > 19 || !passesLuhn(cardDigits)) {
      setFieldError("card-number", "card-number-error", "Informe um número de cartão válido.");
      isValid = false;
    } else {
      setFieldError("card-number", "card-number-error", "");
    }

    if (holderNameInput.value.trim().length === 0) {
      setFieldError("holder-name", "holder-name-error", "Informe o nome impresso no cartão.");
      isValid = false;
    } else {
      setFieldError("holder-name", "holder-name-error", "");
    }

    const expiry = parseExpiry(expiryInput.value);
    if (!expiry) {
      setFieldError("expiry", "expiry-error", "Use o formato MM/AA.");
      isValid = false;
    } else if (isExpired(expiry)) {
      setFieldError("expiry", "expiry-error", "Cartão vencido.");
      isValid = false;
    } else {
      setFieldError("expiry", "expiry-error", "");
    }

    if (!/^\d{3,4}$/.test(cvcInput.value)) {
      setFieldError("cvc", "cvc-error", "Informe 3 ou 4 dígitos.");
      isValid = false;
    } else {
      setFieldError("cvc", "cvc-error", "");
    }

    return isValid;
  };

  // Payload matching the backend schemas (PaymentMethodCreateSchema)
  const buildPayload = () => {
    if (getSelectedType() === "boleto") {
      return { type: "boleto" };
    }
    const expiry = parseExpiry(expiryInput.value);
    return {
      type: "credit_card",
      card_number: cardNumberInput.value.replace(/\D/g, ""),
      holder_name: holderNameInput.value.trim(),
      cvc: cvcInput.value,
      expiration_month: expiry.month,
      expiration_year: expiry.year,
      bank_name: bankNameInput.value.trim() || null
    };
  };

  // "2026-11-18" -> "18/11/2026" (no Date object, so no timezone surprises)
  const formatDate = (isoDate) => isoDate.split("-").reverse().join("/");

  const showSuccess = (result) => {
    if (result.type === "credit_card") {
      successText.textContent = `Cartão com final ${result.last_four} cadastrado com sucesso.`;
    } else {
      successText.textContent =
        `Boleto gerado com vencimento em ${formatDate(result.due_date)}. ` +
        `Código de barras: ${result.barcode}`;
    }
    form.hidden = true;
    successBox.hidden = false;
  };

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (getSelectedType() === "credit_card" && !validateCardFields()) {
      return;
    }

    const submitButton = form.querySelector("button[type='submit']");

    try {
      if (submitButton) submitButton.disabled = true;

      const response = await fetch(`${API_BASE_URL}/api/accounts/${accountId}/payment-methods`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(buildPayload())
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        // Business errors come as a string; request validation errors come as a list.
        const message = typeof errorData.detail === "string"
          ? errorData.detail
          : "Erro ao cadastrar a forma de pagamento. Verifique os dados inseridos.";
        throw new Error(message);
      }

      showSuccess(await response.json());

    } catch (error) {
      console.error("Payment method error:", error);
      alert(error.message || "Não foi possível conectar ao servidor.");
      if (submitButton) submitButton.disabled = false;
    }
  });

  updateVisibleFields();
});
