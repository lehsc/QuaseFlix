const assert = require("node:assert/strict");

const values = new Map();
global.localStorage = {
  getItem: key => values.has(key) ? values.get(key) : null,
  setItem: (key, value) => values.set(key, String(value)),
  removeItem: key => values.delete(key),
};
global.document = { addEventListener: () => {} };
global.window = {
  location: {
    hostname: "lehsc.github.io",
    href: "https://lehsc.github.io/QuaseFlix/pages/login.html",
    search: "",
    reload: () => {},
  },
  fetch: global.fetch,
};

require("../frontend/scripts/pages-api.js");

const request = async (path, options = {}) => {
  const response = await window.fetch(`http://localhost:8000${path}`, options);
  const body = response.status === 204 ? null : await response.json();
  return { response, body };
};

(async () => {
  assert.equal(window.QuaseflixPagesDemo.active, true);

  const login = await request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "demo@quaseflix.com", password: "QuaseFlix123" }),
  });
  assert.equal(login.response.status, 200);
  const authorization = { Authorization: `Bearer ${login.body.token}` };

  const profiles = await request("/api/profiles", { headers: authorization });
  assert.equal(profiles.body.length, 2);
  const selection = await request(`/api/profiles/${profiles.body[0].id}/select`, {
    method: "POST", headers: { ...authorization, "Content-Type": "application/json" }, body: "{}",
  });
  assert.equal(selection.response.status, 200);

  const catalog = await request("/api/catalog?limit=24", { headers: authorization });
  assert.equal(catalog.response.status, 200);
  assert.ok(catalog.body.items.length >= 4);

  const playback = await request("/api/streaming/1", { headers: authorization });
  assert.equal(playback.response.status, 200);
  assert.equal(playback.body.stream_url, "../media/quaseflix-demo.mp4");

  const registration = await request("/api/registration/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "new@example.com" }),
  });
  assert.equal(registration.body.demo_code, "123456");
  const verification = await request("/api/registration/verify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: registration.body.token, code: "123456" }),
  });
  assert.equal(verification.response.status, 200);
  const completion = await request("/api/registration/complete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      token: registration.body.token,
      password: "NewQuaseFlix123",
      full_name: "Nova Pessoa",
      plan_id: 1,
      payment: { type: "boleto" },
    }),
  });
  assert.equal(completion.response.status, 201);
  const newLogin = await request("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "new@example.com", password: "NewQuaseFlix123" }),
  });
  assert.equal(newLogin.response.status, 200);

  console.log("GitHub Pages demo API smoke test passed.");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
