/*
 * GitHub Pages adapter.
 *
 * GitHub Pages only hosts static files, while QuaseFlix normally uses the
 * FastAPI/PostgreSQL application in this repository. On *.github.io this file
 * provides a deterministic browser-local demo API. Local development is left
 * untouched and continues to call http://localhost:8000.
 */
(() => {
  "use strict";

  const isPages = window.location.hostname.endsWith(".github.io");
  const forcedDemo = new URLSearchParams(window.location.search).get("demo") === "1";
  if (!isPages && !forcedDemo) return;

  const STORAGE_KEY = "quaseflix_pages_demo_v1";
  const API_ORIGIN = "http://localhost:8000";
  const DEMO_EMAIL = "demo@quaseflix.com";
  const DEMO_PASSWORD = "QuaseFlix123";
  let memoryState = null;

  const genres = [
    { id: 1, name: "Aventura" },
    { id: 2, name: "Comédia" },
    { id: 3, name: "Drama" },
    { id: 4, name: "Ficção científica" },
    { id: 5, name: "Família" },
  ];

  const media = [
    {
      id: 1, title: "Além das Estrelas", media_type: "movie", release_year: 2025,
      genres: ["Aventura", "Ficção científica"], genre_ids: [1, 4], age_rating: 10,
      synopsis: "Uma equipe improvável atravessa o espaço para encontrar um novo lar.",
      duration_minutes: 2, actors: ["Ana Luz", "Caio Vidal"], directors: ["Lia Ramos"],
      audio_languages: ["Português"], subtitle_languages: ["Português"],
      season_count: 0, episode_count: 0, seasons: [],
    },
    {
      id: 2, title: "A Turma do Bosque", media_type: "series", release_year: 2024,
      genres: ["Comédia", "Família"], genre_ids: [2, 5], age_rating: 0,
      synopsis: "Amigos descobrem que todo dia guarda uma pequena aventura.",
      duration_minutes: 4, actors: ["Bia Sol", "Tom Nunes"], directors: ["Rui Melo"],
      audio_languages: ["Português"], subtitle_languages: ["Português"],
      season_count: 1, episode_count: 2,
      seasons: [{ id: 1, season_number: 1, title: "Novos amigos", episodes: [
        { id: 1, episode_number: 1, title: "O mapa", duration_minutes: 2, director: "Rui Melo" },
        { id: 2, episode_number: 2, title: "A ponte", duration_minutes: 2, director: "Rui Melo" },
      ] }],
    },
    {
      id: 3, title: "Café da Esquina", media_type: "movie", release_year: 2023,
      genres: ["Comédia", "Drama"], genre_ids: [2, 3], age_rating: 12,
      synopsis: "Encontros casuais mudam a rotina de um pequeno café de bairro.",
      duration_minutes: 2, actors: ["Mara Reis", "Leo Paiva"], directors: ["Ivo Cruz"],
      audio_languages: ["Português"], subtitle_languages: ["Português"],
      season_count: 0, episode_count: 0, seasons: [],
    },
    {
      id: 4, title: "Planeta Azul", media_type: "movie", release_year: 2022,
      genres: ["Família"], genre_ids: [5], age_rating: 0,
      synopsis: "Uma viagem leve e educativa pelos oceanos do nosso planeta.",
      duration_minutes: 2, actors: [], directors: ["Nina Costa"],
      audio_languages: ["Português"], subtitle_languages: ["Português"],
      season_count: 0, episode_count: 0, seasons: [],
    },
  ];

  const initialState = () => ({
    nextAccountId: 2,
    nextProfileId: 3,
    nextPaymentId: 2,
    registrations: {},
    progress: {},
    accounts: [{
      id: 1,
      email: DEMO_EMAIL,
      password: DEMO_PASSWORD,
      full_name: "Visitante QuaseFlix",
      status: "trial",
      selectedProfileId: null,
      plan_id: 1,
      profiles: [
        { id: 1, name: "Principal", is_kids: false, genre_ids: [1, 4] },
        { id: 2, name: "Crianças", is_kids: true, genre_ids: [2, 5] },
      ],
      payment_methods: [{ id: 1, type: "boleto", barcode: "00190.00009 01234.567890 12345.678901 1 00000000002590" }],
      invoices: [],
    }],
  });

  const readState = () => {
    if (memoryState) return memoryState;
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved?.accounts?.length) return saved;
    } catch (_) { /* Reset corrupt demo data below. */ }
    const state = initialState();
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch (_) { memoryState = state; }
    return state;
  };

  const writeState = state => {
    memoryState = state;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch (_) { /* The in-memory demo still works when storage is unavailable. */ }
  };
  const json = (body, status = 200) => new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
  const empty = (status = 204) => new Response(null, { status });
  const error = (detail, status = 400) => json({ detail }, status);
  const tokenFor = id => `pages-demo-token-${id}`;
  const accountView = account => ({
    id: account.id, email: account.email, full_name: account.full_name,
    status: account.status, plan_id: account.plan_id,
  });

  const requestBody = async request => {
    try { return await request.clone().json(); }
    catch (_) { return {}; }
  };

  const authenticatedAccount = (request, state) => {
    const header = request.headers.get("Authorization") || "";
    const match = /^Bearer pages-demo-token-(\d+)$/.exec(header);
    return match ? state.accounts.find(item => item.id === Number(match[1])) : null;
  };

  const visibleMedia = account => {
    const selected = account.profiles.find(profile => profile.id === account.selectedProfileId);
    if (!selected) return null;
    return selected.is_kids ? media.filter(item => item.age_rating === 0) : media;
  };

  const summary = item => ({
    id: item.id, title: item.title, media_type: item.media_type,
    release_year: item.release_year, genres: item.genres, age_rating: item.age_rating,
  });

  async function handleRegistration(path, request, state) {
    if (path === "/api/registration/config" && request.method === "GET") {
      return json({ google_client_id: null, mode: "pages-demo" });
    }
    const body = await requestBody(request);
    if (path === "/api/registration/start" && request.method === "POST") {
      const email = String(body.email || "").trim().toLowerCase();
      if (!email.includes("@")) return error("Informe um e-mail válido.", 422);
      if (state.accounts.some(item => item.email.toLowerCase() === email)) return error("E-mail já cadastrado.", 409);
      const token = `registration-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      state.registrations[token] = { email, code: "123456", verified: false };
      writeState(state);
      return json({ token, delivery: "browser-demo", demo_code: "123456" });
    }
    if (path === "/api/registration/verify" && request.method === "POST") {
      const registration = state.registrations[body.token];
      if (!registration) return error("Cadastro expirado. Reinicie o processo.", 404);
      if (String(body.code) !== registration.code) return error("Código inválido. No modo demo, use 123456.", 422);
      registration.verified = true;
      writeState(state);
      return json({ verified: true });
    }
    if (path === "/api/registration/complete" && request.method === "POST") {
      const registration = state.registrations[body.token];
      if (!registration?.verified) return error("Verifique o e-mail antes de continuar.", 409);
      if (String(body.password || "").length < 10) return error("A senha deve ter pelo menos 10 caracteres.", 422);
      const account = {
        id: state.nextAccountId++, email: registration.email, password: body.password,
        full_name: body.full_name || "Assinante QuaseFlix", status: "trial",
        selectedProfileId: null, plan_id: Number(body.plan_id) || 1,
        profiles: [{ id: state.nextProfileId++, name: "Principal", is_kids: false, genre_ids: [] }],
        payment_methods: [], invoices: [],
      };
      if (body.payment?.type === "boleto") {
        account.payment_methods.push({ id: state.nextPaymentId++, type: "boleto", barcode: "00190.00009 01234.567890 12345.678901 1 00000000002590" });
      } else if (body.payment?.type === "credit_card") {
        account.payment_methods.push({ id: state.nextPaymentId++, type: "credit_card", last_four: String(body.payment.card_number || "").slice(-4) });
      }
      state.accounts.push(account);
      delete state.registrations[body.token];
      writeState(state);
      return json({ id: account.id, status: "trial", payment_mode: "simulated" }, 201);
    }
    return error("Rota de cadastro não encontrada.", 404);
  }

  async function handleProfiles(path, request, state, account) {
    if (path === "/api/genres" && request.method === "GET") return json(genres);
    if (path === "/api/profiles" && request.method === "GET") return json(account.profiles);
    if (path === "/api/profiles/current" && request.method === "GET") {
      const profile = account.profiles.find(item => item.id === account.selectedProfileId) || null;
      return json({ profile, restricted: Boolean(profile?.is_kids) });
    }
    const match = /^\/api\/profiles\/(\d+)(\/select)?$/.exec(path);
    const body = await requestBody(request);
    if (path === "/api/profiles" && request.method === "POST") {
      if (account.profiles.length >= 4) return error("Uma conta pode ter no máximo quatro perfis.", 409);
      const name = String(body.name || "").trim();
      if (!name) return error("Informe o nome do perfil.", 422);
      const profile = { id: state.nextProfileId++, name, is_kids: Boolean(body.is_kids), genre_ids: body.genre_ids || [] };
      account.profiles.push(profile);
      writeState(state);
      return json(profile, 201);
    }
    if (!match) return null;
    const profileId = Number(match[1]);
    const index = account.profiles.findIndex(item => item.id === profileId);
    if (index < 0) return error("Perfil não encontrado.", 404);
    if (match[2] && request.method === "POST") {
      const current = account.profiles.find(item => item.id === account.selectedProfileId);
      if (current?.is_kids && !account.profiles[index].is_kids && body.password !== account.password) {
        return error("Senha da conta incorreta.", 403);
      }
      account.selectedProfileId = profileId;
      writeState(state);
      return json({ profile: account.profiles[index], restricted: account.profiles[index].is_kids });
    }
    if (request.method === "PUT") {
      account.profiles[index] = {
        ...account.profiles[index], name: String(body.name || "").trim(),
        is_kids: Boolean(body.is_kids), genre_ids: body.genre_ids || [],
      };
      writeState(state);
      return json(account.profiles[index]);
    }
    if (request.method === "DELETE") {
      if (account.profiles.length === 1) return error("Mantenha pelo menos um perfil.", 409);
      account.profiles.splice(index, 1);
      if (account.selectedProfileId === profileId) account.selectedProfileId = null;
      writeState(state);
      return empty();
    }
    return null;
  }

  function handleCatalog(url, request, account) {
    if (request.method !== "GET") return null;
    const available = visibleMedia(account);
    if (!available) return error("Selecione um perfil.", 409);
    if (url.pathname === "/api/catalog/genres") return json(genres);
    const detailMatch = /^\/api\/catalog\/(\d+)$/.exec(url.pathname);
    if (detailMatch) {
      const item = available.find(entry => entry.id === Number(detailMatch[1]));
      return item ? json(item) : error("Obra não encontrada.", 404);
    }
    if (url.pathname !== "/api/catalog") return null;
    const query = (url.searchParams.get("q") || "").trim().toLocaleLowerCase("pt-BR");
    const type = url.searchParams.get("media_type");
    const genreId = Number(url.searchParams.get("genre_id") || 0);
    const offset = Math.max(0, Number(url.searchParams.get("offset") || 0));
    const limit = Math.max(1, Math.min(100, Number(url.searchParams.get("limit") || 24)));
    const filtered = available.filter(item =>
      (!query || `${item.title} ${item.synopsis}`.toLocaleLowerCase("pt-BR").includes(query)) &&
      (!type || item.media_type === type) && (!genreId || item.genre_ids.includes(genreId))
    );
    const selected = account.profiles.find(profile => profile.id === account.selectedProfileId);
    const suggestions = available.filter(item =>
      !filtered.includes(item) && item.genre_ids.some(id => selected.genre_ids.includes(id))
    ).slice(0, 3).map(summary);
    return json({ items: filtered.slice(offset, offset + limit).map(summary), total: filtered.length, limit, offset, suggestions });
  }

  async function handleStreaming(url, request, state, account) {
    const match = /^\/api\/streaming\/(\d+)(\/progress)?$/.exec(url.pathname);
    if (!match) return null;
    const available = visibleMedia(account);
    if (!available) return error("Selecione um perfil.", 409);
    const item = available.find(entry => entry.id === Number(match[1]));
    if (!item) return error("Conteúdo não encontrado.", 404);
    const episodeId = Number(url.searchParams.get("episode_id") || 0) || null;
    const episode = episodeId ? item.seasons.flatMap(season => season.episodes).find(entry => entry.id === episodeId) : null;
    if (item.media_type === "series" && !episode) return error("Selecione um episódio.", 409);
    const key = `${account.id}:${account.selectedProfileId}:${item.id}:${episodeId || 0}`;
    if (match[2] && request.method === "PUT") {
      const body = await requestBody(request);
      state.progress[key] = {
        position_seconds: Number(body.position_seconds) || 0,
        completed: Number(body.position_seconds) >= 28,
        audio_language: body.audio_language || null,
        subtitle_language: body.subtitle_language || null,
      };
      writeState(state);
      return json(state.progress[key]);
    }
    if (request.method !== "GET") return null;
    const progress = state.progress[key] || {};
    return json({
      media_id: item.id, episode_id: episodeId, title: item.title,
      episode_title: episode?.title || null, content_type: episode ? "episode" : "movie",
      stream_url: "../media/quaseflix-demo.mp4", stream_type: "video/mp4", adaptive: false,
      duration_seconds: 30, resume_position_seconds: progress.completed ? 0 : progress.position_seconds || 0,
      completed: Boolean(progress.completed),
      audio_tracks: [{ language: "Português" }], subtitle_tracks: [],
      selected_audio: progress.audio_language || "Português", selected_subtitle: null,
    });
  }

  async function handleSubscription(path, request, state, account) {
    if (path === "/api/subscription/login" && request.method === "POST") {
      const body = await requestBody(request);
      const found = state.accounts.find(item => item.email.toLowerCase() === String(body.email || "").toLowerCase());
      return found && found.password === body.password ? json({ token: tokenFor(found.id) }) : error("E-mail ou senha incorretos.", 401);
    }
    if (!account) return error("Sessão inválida.", 401);
    if (path === "/api/subscription" && request.method === "GET") {
      return json({
        status: account.status,
        next_billing_at: account.status === "canceled" ? null : new Date(Date.now() + 30 * 86400000).toISOString(),
        outstanding: account.invoices.filter(item => !item.paid_at).reduce((sum, item) => sum + item.amount, 0),
        invoices: account.invoices, payment_methods: account.payment_methods,
      });
    }
    if (path === "/api/subscription/payment-methods" && request.method === "POST") {
      const method = { id: state.nextPaymentId++, type: "boleto", barcode: "00190.00009 01234.567890 12345.678901 1 00000000002590" };
      account.payment_methods.push(method);
      writeState(state);
      return json(method, 201);
    }
    if (path === "/api/subscription/pay" && request.method === "POST") {
      account.invoices.forEach(item => { if (!item.paid_at) item.paid_at = new Date().toISOString(); });
    } else if (path === "/api/subscription/cancel" && request.method === "POST") {
      account.status = "canceled";
    } else if (path === "/api/subscription/restore" && request.method === "POST") {
      account.status = "active";
    } else return null;
    writeState(state);
    return json({ status: account.status });
  }

  async function demoFetch(input, init) {
    const request = new Request(input, init);
    const url = new URL(request.url, window.location.href);
    if (url.origin !== API_ORIGIN || !url.pathname.startsWith("/api/")) return null;
    const state = readState();

    if (url.pathname.startsWith("/api/registration/")) return handleRegistration(url.pathname, request, state);
    if (url.pathname === "/api/plans" && request.method === "GET") {
      return json([{ id: 1, name: "Padrão", price: 25.90, description: "Acesso completo ao catálogo de demonstração." }]);
    }
    if (url.pathname === "/api/auth/login" && request.method === "POST") {
      const body = await requestBody(request);
      const account = state.accounts.find(item => item.email.toLowerCase() === String(body.email || "").trim().toLowerCase());
      if (!account || account.password !== body.password) return error("E-mail ou senha incorretos.", 401);
      if (account.status === "canceled") return error("Esta conta foi cancelada.", 403);
      return json({ token: tokenFor(account.id), account: accountView(account) });
    }
    if (url.pathname === "/api/subscription/login") return handleSubscription(url.pathname, request, state, null);

    const account = authenticatedAccount(request, state);
    if (!account) return error("Sessão inválida.", 401);

    if (/^\/api\/accounts\/\d+\/plan$/.test(url.pathname) && request.method === "PUT") {
      const body = await requestBody(request);
      account.plan_id = Number(body.plan_id) || 1;
      writeState(state);
      return json({ account_id: account.id, plan_id: account.plan_id });
    }
    if (/^\/api\/accounts\/\d+\/payment-methods$/.test(url.pathname) && request.method === "POST") {
      const body = await requestBody(request);
      const method = body.type === "credit_card"
        ? { id: state.nextPaymentId++, type: "credit_card", last_four: String(body.card_number || "").slice(-4) }
        : { id: state.nextPaymentId++, type: "boleto", due_date: new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10), barcode: "00190.00009 01234.567890 12345.678901 1 00000000002590" };
      account.payment_methods.push(method);
      writeState(state);
      return json(method, 201);
    }

    const profileResponse = await handleProfiles(url.pathname, request, state, account);
    if (profileResponse) return profileResponse;
    const catalogResponse = handleCatalog(url, request, account);
    if (catalogResponse) return catalogResponse;
    const streamingResponse = await handleStreaming(url, request, state, account);
    if (streamingResponse) return streamingResponse;
    const subscriptionResponse = await handleSubscription(url.pathname, request, state, account);
    if (subscriptionResponse) return subscriptionResponse;
    return error("Recurso de demonstração não encontrado.", 404);
  }

  const nativeFetch = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const response = await demoFetch(input, init);
    return response || nativeFetch(input, init);
  };

  window.QuaseflixPagesDemo = {
    active: true,
    credentials: { email: DEMO_EMAIL, password: DEMO_PASSWORD },
    reset: () => {
      memoryState = null;
      try { localStorage.removeItem(STORAGE_KEY); } catch (_) { /* Already reset in memory. */ }
      window.location.reload();
    },
  };

  document.addEventListener("DOMContentLoaded", () => {
    const banner = document.createElement("aside");
    banner.className = "pages-demo-banner";
    banner.setAttribute("role", "status");
    banner.innerHTML = `<strong>Modo demonstração</strong><span>Os dados ficam somente neste navegador. Acesso: ${DEMO_EMAIL} / ${DEMO_PASSWORD}</span>`;
    const reset = document.createElement("button");
    reset.type = "button";
    reset.textContent = "Restaurar demo";
    reset.addEventListener("click", window.QuaseflixPagesDemo.reset);
    banner.append(reset);
    document.body.prepend(banner);
  });
})();
