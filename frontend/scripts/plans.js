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
      <label style="display: flex; align-items: flex-start; gap: 1rem; padding: 1.15rem; background-color: rgba(22, 22, 22, 0.9); border: 1px solid rgba(128, 128, 128, 0.5); border-radius: 4px; cursor: pointer; transition: border-color 0.2s;">
        <input type="radio" name="selected-plan" value="${plan.id}" ${index === 0 ? "checked" : ""} style="margin-top: 0.2rem; accent-color: #e50914;" />
        <div style="flex: 1;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
            <strong style="font-size: 1.05rem; color: #fff;">${plan.name}</strong>
            <span style="font-weight: 700; color: #e50914;">R$ ${plan.price.toFixed(2).replace('.', ',')}</span>
          </div>
          <p style="font-size: 0.9rem; color: #b3b3b3; line-height: 1.4;">${plan.description || "Acesso completo ao catálogo."}</p>
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