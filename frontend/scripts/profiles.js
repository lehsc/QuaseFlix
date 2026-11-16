/**
 * Post-login screen (placeholder): checks the session with the server and logs out.
 * Every page that needs a logged-in user can follow the same pattern (RF04).
 */
document.addEventListener("DOMContentLoaded", async () => {
  const API_BASE_URL = "http://localhost:8000";
  const LOGIN_URL = "./login.html";

  const welcomeText = document.getElementById("welcome-text");
  const logoutButton = document.getElementById("btn-logout");

  const goToLogin = () => {
    QuaseflixSession.clear();
    window.location.href = LOGIN_URL;
  };

  logoutButton.addEventListener("click", goToLogin);

  const token = QuaseflixSession.getToken();
  if (!token) {
    window.location.href = LOGIN_URL;
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    });

    // Invalid or expired token, canceled account, expired trial...
    if (!response.ok) {
      goToLogin();
      return;
    }

    const { account } = await response.json();
    welcomeText.textContent = `Você entrou como ${account.email}.`;

  } catch (error) {
    console.error("Session check error:", error);
    welcomeText.textContent = "Não foi possível conectar ao servidor.";
  }
});
