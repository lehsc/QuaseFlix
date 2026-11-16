document.addEventListener("DOMContentLoaded", async () => {
  if (!CatalogAPI.initialize()) return;
  const { element } = CatalogAPI;
  const form = document.getElementById("catalog-filters");
  const search = document.getElementById("search");
  const type = document.getElementById("media-type");
  const genre = document.getElementById("genre");
  const status = document.getElementById("catalog-status");
  const results = document.getElementById("catalog-results");
  const suggestions = document.getElementById("suggestions");
  const suggestionItems = document.getElementById("suggestion-items");
  const pagination = document.getElementById("pagination");
  const previous = document.getElementById("previous-page");
  const next = document.getElementById("next-page");
  const retry = document.getElementById("retry");
  const pageSize = 24;
  let offset = 0;
  let controller;
  let desiredGenre = "";

  const restoreFilters = () => {
    const params = new URLSearchParams(window.location.search);
    search.value = (params.get("q") || "").slice(0, 200);
    type.value = ["movie", "series"].includes(params.get("media_type")) ? params.get("media_type") : "";
    desiredGenre = /^[1-9]\d*$/.test(params.get("genre_id")) ? params.get("genre_id") : "";
    genre.value = desiredGenre;
    const requestedOffset = Number(params.get("offset"));
    offset = Number.isSafeInteger(requestedOffset) && requestedOffset >= 0 ? requestedOffset : 0;
  };

  const parameters = () => {
    const params = new URLSearchParams();
    if (search.value.trim()) params.set("q", search.value.trim());
    if (type.value) params.set("media_type", type.value);
    if (genre.value) params.set("genre_id", genre.value);
    if (offset) params.set("offset", offset);
    return params;
  };

  const card = (media) => {
    const link = element("a", undefined, "media-card");
    const params = parameters();
    params.set("id", media.id);
    link.href = `./media.html?${params}`;
    link.append(element("span", media.media_type === "movie" ? "Filme" : "Série", "eyebrow"),
      element("h3", media.title), element("p", media.release_year ?? "Ano não informado", "muted"),
      element("p", media.genres.join(" · ") || "Gênero não informado"));
    return link;
  };

  const load = async (updateHistory = true) => {
    controller?.abort();
    const request = new AbortController();
    controller = request;
    const params = parameters();
    if (updateHistory) history.replaceState(null, "", `./catalog.html${params.size ? `?${params}` : ""}`);
    params.set("limit", pageSize);
    status.textContent = "Carregando catálogo…";
    results.replaceChildren();
    results.setAttribute("aria-busy", "true");
    suggestions.hidden = pagination.hidden = retry.hidden = true;
    try {
      const data = await CatalogAPI.get(`?${params}`, request.signal);
      if (request.signal.aborted) return;
      status.textContent = data.total
        ? `${data.total} obra(s) encontrada(s).`
        : search.value.trim() ? "Nenhuma obra encontrada para sua busca." : "Nenhuma obra disponível com esses filtros.";
      for (const [format, label] of [["movie", "Filmes"], ["series", "Séries"]]) {
        const items = data.items.filter(item => item.media_type === format);
        if (!items.length) continue;
        const section = element("section");
        const grid = element("div", undefined, "media-grid");
        items.forEach(item => grid.append(card(item)));
        section.append(element("h2", label), grid);
        results.append(section);
      }
      suggestionItems.replaceChildren(...data.suggestions.map(card));
      suggestions.hidden = !data.suggestions.length;
      pagination.hidden = data.total <= pageSize && offset === 0;
      previous.disabled = offset === 0;
      next.disabled = offset + pageSize >= data.total;
      document.getElementById("page-info").textContent = `Página ${Math.floor(offset / pageSize) + 1}`;
      if (data.total && !data.items.length) status.textContent = "Esta página está vazia. Volte à página anterior ou limpe os filtros.";
    } catch (error) {
      if (request.signal.aborted) return;
      status.textContent = error instanceof TypeError ? "Não foi possível conectar ao servidor." : error.message;
      retry.hidden = false;
    } finally {
      if (!request.signal.aborted) results.setAttribute("aria-busy", "false");
    }
  };

  const filter = () => { offset = 0; load(); };
  form.addEventListener("submit", event => { event.preventDefault(); filter(); });
  type.addEventListener("change", filter);
  genre.addEventListener("change", filter);
  form.addEventListener("reset", event => {
    event.preventDefault();
    search.value = type.value = genre.value = "";
    filter();
  });
  previous.addEventListener("click", () => { offset = Math.max(0, offset - pageSize); load(); });
  next.addEventListener("click", () => { offset += pageSize; load(); });
  retry.addEventListener("click", () => load());
  window.addEventListener("popstate", () => { restoreFilters(); load(false); });
  restoreFilters();
  try {
    const genres = await CatalogAPI.get("/genres");
    genres.forEach(item => {
      const option = element("option", item.name);
      option.value = item.id;
      genre.append(option);
    });
    genre.value = desiredGenre;
  } catch {
    document.getElementById("genre-status").textContent = "Não foi possível carregar os gêneros. Recarregue a página para tentar novamente.";
  }
  load();
});
