// Run without a browser or extra packages: node --test tests/test_register.js
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

async function submitRegistration(response) {
  const source = readFileSync(join(__dirname, "../frontend/scripts/register.js"), "utf8");
  const start = source.indexOf("async function post(");
  const end = source.indexOf("function onSubmit(", start);
  const context = { API_BASE: "http://localhost:8000/api/registration", fetch: async () => response };
  vm.createContext(context);
  vm.runInContext(source.slice(start, end), context);
  try {
    const result = await context.post("/complete", { phone: null });
    return { alerts: [], result };
  } catch (error) {
    return { alerts: [error.message], fieldName: error.fieldName };
  }
}

test("validation errors retain their message and field for inline display", async () => {
  const result = await submitRegistration({ ok: false, json: async () => ({ detail: [
    { loc: ["body", "phone"], msg: "Input should be a valid string" },
    { loc: ["body", "password"], msg: "String should have at most 128 characters" }
  ] }) });
  assert.deepEqual(result.alerts, [
    "Input should be a valid string"
  ]);
  assert.equal(result.fieldName, "phone");
});

test("plain API error messages remain readable", async () => {
  const result = await submitRegistration({ ok: false, json: async () => ({ detail: "Unable to register account." }) });
  assert.deepEqual(result.alerts, ["Unable to register account."]);
});

test("unexpected error bodies use a readable fallback", async () => {
  for (const body of [null, {}, { detail: {} }, { detail: [null, {}] }]) {
    const result = await submitRegistration({ ok: false, json: async () => body });
    assert.deepEqual(result.alerts, ["Verifique os dados informados."]);
  }
});

test("verified registration accepts a successful completion response", async () => {
  const result = await submitRegistration({ ok: true, json: async () => ({ id: 123 }) });
  assert.equal(result.result.id, 123);
  assert.deepEqual(result.alerts, []);

});
