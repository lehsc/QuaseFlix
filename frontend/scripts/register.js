const API_BASE = "http://localhost:8000/api/registration";
const startForm = document.querySelector("#start");
const verifyForm = document.querySelector("#verify");
const completeForm = document.querySelector("#complete");
const statusText = document.querySelector("#status");
const completeStatus = document.querySelector("#complete-status");
const googleStatus = document.querySelector("#google-status");
const cardFields = document.querySelector("#card");
const googleUnavailable = document.querySelector("#google-unavailable");

let token = sessionStorage.getItem("registration_token");
let verified = sessionStorage.getItem("registration_verified") === "yes";

function showError(message, form = null) {
  statusText.textContent = message;
  completeStatus.textContent = form === completeForm ? message : "";
  if (form === completeForm && message) {
    completeStatus.scrollIntoView({ block: "nearest" });
  }
}

function clearFieldError(field) {
  field.classList.remove("input-error");
  field.removeAttribute("aria-invalid");
  const note = field.closest("label")?.querySelector(".field-error");
  if (note) note.remove();
}

function markFieldError(field, message) {
  clearFieldError(field);
  field.classList.add("input-error");
  field.setAttribute("aria-invalid", "true");
  const note = document.createElement("span");
  note.className = "field-error";
  note.textContent = message;
  field.closest("label")?.append(note);
  field.scrollIntoView({ block: "nearest" });
}

function markServerError(message, form, explicitField = null) {
  const lower = message.toLowerCase();
  const fieldName = explicitField || (lower.includes("cpf") ? "cpf"
    : lower.includes("email") || lower.includes("e-mail") ? "email"
    : lower.includes("code") || lower.includes("código") ? "code"
    : lower.includes("password") || lower.includes("senha") ? "password"
    : lower.includes("full name") || lower.includes("nome") ? "full_name"
    : lower.includes("birth date") ? "birth_date"
    : lower.includes("address") || lower.includes("endereço") ? "address"
    : lower.includes("plan") || lower.includes("plano") ? "plan_id"
    : lower.includes("card") || lower.includes("cartão") ? "card_number"
    : null);
  if (fieldName) {
    const field = form.elements.namedItem(fieldName);
    if (field) markFieldError(field, message);
  }
}

for (const form of [startForm, verifyForm, completeForm]) {
  for (const field of form.querySelectorAll("input, select")) {
    field.addEventListener("input", () => clearFieldError(field));
    field.addEventListener("change", () => clearFieldError(field));
  }
}

function render() {
  startForm.hidden = Boolean(token);
  verifyForm.hidden = !token || verified;
  completeForm.hidden = !verified;
}

function saveRegistration(value, confirmed) {
  token = value;
  verified = confirmed;
  sessionStorage.setItem("registration_token", token);
  sessionStorage.setItem("registration_verified", confirmed ? "yes" : "no");
  showError("");
  render();
}

async function post(path, data) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const result = await response.json();
  if (!response.ok) {
    if (typeof result?.detail === "string") throw new Error(result.detail);
    const first = Array.isArray(result?.detail) ? result.detail[0] : null;
    const error = new Error(first?.msg || "Verifique os dados informados.");
    error.fieldName = first?.loc?.at(-1);
    throw error;
  }
  return result;
}

function onSubmit(form, handler) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    showError("");
    try {
      await handler(new FormData(form));
    } catch (error) {
      showError(error.message || "Não foi possível concluir a solicitação.", form);
      markServerError(error.message || "", form, error.fieldName);
    } finally {
      button.disabled = false;
    }
  });
}

onSubmit(startForm, async (data) => {
  const result = await post("/start", { email: data.get("email") });
  saveRegistration(result.token, false);
  statusText.textContent = "Código enviado. Consulte a caixa de saída local e digite-o abaixo.";
});

onSubmit(verifyForm, async (data) => {
  await post("/verify", { token, code: data.get("code") });
  saveRegistration(token, true);
  statusText.textContent = "E-mail verificado. Complete o cadastro abaixo.";
});

function updatePaymentFields() {
  const usesCard = completeForm.elements.namedItem("type").value === "credit_card";
  cardFields.hidden = !usesCard;
  for (const field of cardFields.querySelectorAll("input")) {
    field.required = usesCard;
    field.disabled = !usesCard;
  }
}
completeForm.elements.namedItem("type").addEventListener("change", updatePaymentFields);
updatePaymentFields();

// Native HTML validation prevents submit from firing. Explain the blocked field
// beside the final button so a click never appears to do nothing.
completeForm.addEventListener("invalid", (event) => {
  const field = event.target;
  const label = field.closest("label")?.textContent.trim() || field.name;
  showError(`${label}: ${field.validationMessage}`, completeForm);
  markFieldError(field, field.validationMessage);
}, true);

onSubmit(completeForm, async (data) => {
  const payload = Object.fromEntries(data);
  payload.token = token;
  payload.plan_id = Number(payload.plan_id);
  payload.phone = payload.phone || null;
  payload.payment = { type: payload.type };
  if (payload.type === "credit_card") {
    for (const key of ["card_number", "holder_name", "cvc", "expiration_month", "expiration_year"]) {
      payload.payment[key] = key.startsWith("expiration_") ? Number(payload[key]) : payload[key];
    }
  }
  for (const key of ["type", "card_number", "holder_name", "cvc", "expiration_month", "expiration_year"]) {
    delete payload[key];
  }
  await post("/complete", payload);
  sessionStorage.removeItem("registration_token");
  sessionStorage.removeItem("registration_verified");
  location.href = "login.html";
});

document.querySelector("#restart").addEventListener("click", () => {
  sessionStorage.removeItem("registration_token");
  sessionStorage.removeItem("registration_verified");
  location.reload();
});

fetch("http://localhost:8000/api/plans")
  .then((response) => {
    if (!response.ok) throw new Error("Não foi possível carregar os planos.");
    return response.json();
  })
  .then((plans) => {
    const selector = completeForm.elements.namedItem("plan_id");
    for (const plan of plans) {
      const option = document.createElement("option");
      option.value = plan.id;
      option.textContent = `${plan.name} — R$ ${Number(plan.price).toFixed(2)}`;
      selector.append(option);
    }
  })
  .catch((error) => showError(error.message, completeForm));

fetch(`${API_BASE}/config`)
  .then((response) => response.json())
  .then((config) => {
    if (!config.google_client_id) {
      googleStatus.textContent = "A opção de continuar com Google está indisponível no momento.";
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.onerror = () => {
      googleStatus.textContent = "Não foi possível carregar a opção de continuar com Google.";
    };
    script.onload = () => {
      googleUnavailable.hidden = true;
      googleStatus.textContent = "";
      google.accounts.id.initialize({
        client_id: config.google_client_id,
        callback: async (response) => {
          try {
            const result = await post("/google", { credential: response.credential });
            if (result.access_token) {
              sessionStorage.setItem("quaseflix_token", result.access_token);
              sessionStorage.setItem("quaseflix_account", JSON.stringify(result.account));
              location.href = "profiles.html";
            } else {
              saveRegistration(result.token, true);
            }
          } catch (error) {
            showError(error.message);
          }
        },
      });
      google.accounts.id.renderButton(document.querySelector("#google"), {
        theme: "outline", size: "large",
      });
    };
    document.head.append(script);
  })
  .catch(() => {
    googleStatus.textContent = "Não foi possível verificar a disponibilidade do cadastro com Google.";
  });

render();
