const googleStatus = document.querySelector("#google-status");
const unavailableButton = document.querySelector("#google-unavailable");

fetch("http://localhost:8000/api/registration/config")
  .then((response) => response.json())
  .then((config) => {
    if (!config.google_client_id) {
      googleStatus.textContent = "Entrar com Google indisponível: configure GOOGLE_CLIENT_ID no servidor.";
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.onerror = () => {
      googleStatus.textContent = "Não foi possível carregar o botão do Google.";
    };
    script.onload = () => {
      google.accounts.id.initialize({
        client_id: config.google_client_id,
        callback: async (response) => {
          try {
            const reply = await fetch("http://localhost:8000/api/registration/google", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ credential: response.credential }),
            });
            const data = await reply.json();
            if (!reply.ok) throw new Error(data.detail || "Não foi possível entrar com Google.");
            if (data.access_token) {
              QuaseflixSession.save(data.access_token, data.account);
              location.href = "profiles.html";
            } else {
              sessionStorage.setItem("registration_token", data.token);
              sessionStorage.setItem("registration_verified", "yes");
              location.href = "register.html";
            }
          } catch (error) {
            const alert = document.querySelector("#login-error");
            alert.hidden = false;
            alert.textContent = error.message;
          }
        },
      });
      google.accounts.id.renderButton(document.querySelector("#google-login"), {
        theme: "outline", size: "large",
      });
      unavailableButton.hidden = true;
      googleStatus.textContent = "";
    };
    document.head.append(script);
  })
  .catch(() => {
    googleStatus.textContent = "Não foi possível verificar a configuração do Google.";
  });
