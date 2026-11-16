// Run without a browser or extra packages: node --test tests/test_register.js
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

async function submitRegistration(response) {
  const elements = new Map();
  const handlers = new Map();
  const alerts = [];
  let sentPayload;
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      value: "", textContent: "", disabled: false,
      classList: { add() {}, remove() {} },
      addEventListener(event, callback) { handlers.set(`${id}:${event}`, callback); },
      querySelector() { return element("submit"); }
    });
    return elements.get(id);
  };
  for (const [id, value] of Object.entries({
    email: "person@example.com", password: "test-password", cpf: "12345678901",
    "birth-date": "2000-01-01", phone: "", address: "Test address"
  })) element(id).value = value;

  const context = {
    document: {
      getElementById: element,
      addEventListener(event, callback) { callback(); }
    },
    fetch: async (url, options) => {
      sentPayload = JSON.parse(options.body);
      return response;
    },
    alert: message => alerts.push(message),
    console: { error() {} },
    sessionStorage: { setItem() {} },
    window: { location: { href: "" } }
  };
  vm.runInNewContext(readFileSync(join(__dirname, "../frontend/scripts/register.js"), "utf8"), context);
  await handlers.get("register-form:submit")({ preventDefault() {} });
  return { alerts, sentPayload, button: element("submit"), destination: context.window.location.href };
}

test("validation objects are displayed as field names and messages", async () => {
  const result = await submitRegistration({ ok: false, json: async () => ({ detail: [
    { loc: ["body", "phone"], msg: "Input should be a valid string" },
    { loc: ["body", "password"], msg: "String should have at most 128 characters" }
  ] }) });
  assert.deepEqual(result.alerts, [
    "Telefone: Input should be a valid string\nSenha: String should have at most 128 characters"
  ]);
  assert.equal(result.button.disabled, false);
});

test("plain API error messages remain readable", async () => {
  const result = await submitRegistration({ ok: false, json: async () => ({ detail: "Unable to register account." }) });
  assert.deepEqual(result.alerts, ["Unable to register account."]);
});

test("unexpected error bodies use a readable fallback", async () => {
  for (const body of [null, {}, { detail: {} }, { detail: [null, {}] }]) {
    const result = await submitRegistration({ ok: false, json: async () => body });
    assert.deepEqual(result.alerts, ["Erro ao realizar o cadastro. Verifique os dados inseridos."]);
    assert.equal(result.button.disabled, false);
  }
});

test("registration without a phone sends null and continues on success", async () => {
  const result = await submitRegistration({ ok: true, json: async () => ({ id: 123 }) });
  assert.equal(result.sentPayload.phone, null);
  assert.deepEqual(result.alerts, []);
  assert.equal(result.destination, "./plans.html");
});
