/* Shared authenticated requests for catalog pages. */
const CatalogAPI = (() => {
  const logout = () => {
    QuaseflixSession.clear();
    window.location.href = "./login.html";
  };

  const initialize = () => {
    document.getElementById("btn-logout").addEventListener("click", logout);
    if (!QuaseflixSession.getToken()) {
      logout();
      return false;
    }
    return true;
  };

  const get = async (path, signal) => {
    const response = await fetch(`http://localhost:8000/api/catalog${path}`, {
      headers: { Authorization: `Bearer ${QuaseflixSession.getToken()}` }, signal
    });
    if ([401, 402, 403].includes(response.status)) {
      logout();
      throw new Error("Sua sessão não permite acessar o catálogo. Entre novamente.");
    }
    if (!response.ok) {
      const error = new Error(response.status === 404
        ? "Esta obra não está disponível no catálogo."
        : "Não foi possível carregar o catálogo. Tente novamente.");
      error.status = response.status;
      throw error;
    }
    return response.json();
  };

  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    // Catalog data is plain text; never interpret titles/synopses as HTML.
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };

  return { get, initialize, element };
})();
