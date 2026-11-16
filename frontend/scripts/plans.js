/**
 * Plans selection handler: fetches plans, handles selection and updates backend
 */
document.addEventListener("DOMContentLoaded", async () => {
  const API_BASE_URL = "http://localhost:8000";

  // Verify if account ID exists in session
  const accountId = JSON.parse(sessionStorage.getItem("quaseflix_account") || "null")?.id;
  if (!accountId) {
    window.location.href = "./login.html";
    return;
  }

  const plansContainer = document.getElementById("plans-container");
  const plansForm = document.getElementById("plans-form");
  const plansError = document.getElementById("plans-error");

  try {
    // Fetch plans from backend
    const response = await fetch(`${API_BASE_URL}/api/plans`);
    if (!response.ok) throw new Error("Não foi possível carregar os planos.");
    
    const plans = await response.json();

    // Render options dynamically
    plansContainer.innerHTML = plans.map((plan, index) => `
      <label class="plan-option">
        <input type="radio" name="selected-plan" value="${plan.id}" ${index === 0 ? "checked" : ""} />
        <div class="plan-option-body">
          <div class="plan-option-heading">
            <strong>${plan.name}</strong>
            <span class="plan-price">R$ ${plan.price.toFixed(2).replace('.', ',')}</span>
          </div>
          <p>${plan.description || "Acesso completo ao catálogo."}</p>
        </div>
      </label>
    `).join("");

  } catch (error) {
    console.error("Error loading plans:", error);
    plansError.textContent = "Erro ao buscar os planos disponíveis no servidor.";
  }

  plansForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    plansError.textContent = "";

    const selectedRadio = plansForm.querySelector("input[name='selected-plan']:checked");
    if (!selectedRadio) {
      plansError.textContent = "Por favor, selecione um plano.";
      return;
    }

    const planId = Number(selectedRadio.value);
    const submitButton = plansForm.querySelector("button[type='submit']");

    try {
      if (submitButton) submitButton.disabled = true;

      // Update account plan via API
      const response = await fetch(`${API_BASE_URL}/api/accounts/${accountId}/plan`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${sessionStorage.getItem("quaseflix_token") || ""}`
        },
        body: JSON.stringify({ plan_id: planId })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Erro ao associar o plano à conta.");
      }

      // Proceed to payment page seamlessly
      window.location.href = "./payment.html";

    } catch (error) {
      console.error("Plan selection error:", error);
      plansError.textContent = error.message || "Erro ao conectar com o servidor.";
      if (submitButton) submitButton.disabled = false;
    }
  });
});
