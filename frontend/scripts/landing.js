/**
 * Landing page event handlers for QuaseFlix
 */
document.addEventListener("DOMContentLoaded", () => {
  const createAccountBtn = document.getElementById("btn-create-account");

  if (createAccountBtn) {
    createAccountBtn.addEventListener("click", () => {
      // Navigate to the first step of the registration flow
      window.location.href = "./pages/register.html";
    });
  }
});