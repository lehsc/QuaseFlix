const api = 'http://localhost:8000/api/subscription';
let token = sessionStorage.getItem('subscription_token') || sessionStorage.getItem('quaseflix_token');
const message = document.querySelector('#message');
const login_form = document.querySelector('#management-login');
const panel = document.querySelector('#subscription');

const statusLabels = {
  trial: 'Período gratuito',
  active: 'Ativa',
  canceled: 'Cancelada'
};

const errorLabels = {
  'Select an owned, valid payment method.': 'Selecione uma forma de pagamento válida.',
  'Settle outstanding invoices first.': 'Pague os débitos pendentes antes de continuar.',
  'Account not found.': 'Conta não encontrada.',
  'Choose a valid plan before billing.': 'Escolha um plano válido antes de continuar.'
};

function formatDate(value) {
  if (!value) return 'não agendada';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat('pt-BR').format(date);
}

function formatPaymentType(type) {
  return type === 'credit_card' ? 'Cartão de crédito' : type === 'boleto' ? 'Boleto' : type;
}

async function request(path = '', body) {
  const response = await fetch(api + path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token || ''}`},
    ...(body === undefined ? {} : {body: JSON.stringify(body)})
  });
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) logout();
    const detail = typeof data.detail === 'string' ? data.detail : 'Verifique os dados informados.';
    throw new Error(errorLabels[detail] || detail);
  }
  return data;
}
function logout() {
  for (const key of ['subscription_token', 'quaseflix_token', 'quaseflix_account', 'quaseflix_profile']) sessionStorage.removeItem(key);
  token = null;
  login_form.hidden = false;
  panel.hidden = true;
}
async function refresh() {
  const data = await request();
  login_form.hidden = true;
  panel.hidden = false;
  document.querySelector('#summary').textContent = `Situação: ${statusLabels[data.status] || data.status}. Próxima cobrança: ${formatDate(data.next_billing_at)}.`;
  document.querySelector('#outstanding').textContent = `Débitos: R$ ${Number(data.outstanding).toFixed(2).replace('.', ',')}`;
  const table = document.querySelector('#invoices');
  table.replaceChildren();
  for (const invoice of data.invoices) {
    const row = table.insertRow();
    for (const value of [`R$ ${Number(invoice.amount).toFixed(2).replace('.', ',')}`, formatDate(invoice.due_at), invoice.paid_at ? 'Pago' : 'Pendente']) row.insertCell().textContent = value;
    if (invoice.barcode && !invoice.paid_at) {
      const detail = table.insertRow().insertCell();
      detail.colSpan = 3;
      detail.textContent = `Boleto simulado: ${invoice.barcode}`;
      detail.style.overflowWrap = 'anywhere';
    }
  }
  const select = document.querySelector('#payment-method');
  select.replaceChildren();
  for (const method of data.payment_methods) {
    const option = document.createElement('option');
    option.value = method.id;
    option.textContent = `${formatPaymentType(method.type)} (cadastro ${method.id})`;
    select.append(option);
  }
  document.querySelector('#cancel').hidden = data.status === 'canceled';
  document.querySelector('#restore').hidden = data.status !== 'canceled';
  document.querySelector('#pay').disabled = Number(data.outstanding) === 0 || !data.payment_methods.length;
}
async function perform(button, operation) {
  button.disabled = true;
  message.textContent = '';
  try { await operation(); } catch (error) { message.textContent = error.message; }
  finally { button.disabled = false; }
}
login_form.onsubmit = event => {
  event.preventDefault();
  perform(login_form.querySelector('button'), async () => {
    const data = await request('/login', Object.fromEntries(new FormData(login_form)));
    token = data.token;
    sessionStorage.setItem('subscription_token', token);
    login_form.reset();
    await refresh();
  });
};
document.querySelector('#logout').onclick = logout;
for (const action of ['pay', 'cancel', 'restore', 'add-boleto']) {
  const button = document.querySelector(`#${action}`);
  button.onclick = () => perform(button, async () => {
    if (action === 'cancel' && !confirm('Cancelar a assinatura e encerrar o acesso? Débitos pendentes precisam ser pagos primeiro.')) return;
    if (action === 'pay' && !confirm('Confirmar a quitação simulada de todos os débitos?')) return;
    if (action === 'restore' && !confirm('Restaurar a assinatura? Fora do trial ou período já pago, será gerada uma nova cobrança simulada.')) return;
    const body = action === 'pay' ? {payment_method_id: Number(document.querySelector('#payment-method').value)} : action === 'add-boleto' ? {type: 'boleto'} : {};
    await request(action === 'add-boleto' ? '/payment-methods' : `/${action}`, body);
    if (action === 'cancel') { logout(); message.textContent = 'Assinatura cancelada. Entre aqui novamente para restaurar.'; }
    else await refresh();
  });
}
if (token) refresh().catch(error => {message.textContent = error.message;});
