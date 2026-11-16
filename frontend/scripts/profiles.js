document.addEventListener('DOMContentLoaded', () => {
  const api = 'http://localhost:8000/api';
  const token = QuaseflixSession.getToken();
  const status = document.querySelector('#status');
  const editor = document.querySelector('#editor');
  const form = document.querySelector('#profile-form');
  const add_button = document.querySelector('#add-profile');
  let profiles = [];
  let genres = [];
  let selection = {profile: null, restricted: false};
  let editing = null;
  let busy = false;

  function logout() {
    QuaseflixSession.clear();
    sessionStorage.removeItem('subscription_token');
    location.href = './login.html';
  }
  document.querySelector('#logout').onclick = logout;
  if (!token) { logout(); return; }

  async function request(path, method = 'GET', body) {
    let response;
    try {
      response = await fetch(api + path, {
        method,
        headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'},
        ...(body === undefined ? {} : {body: JSON.stringify(body)})
      });
    } catch {
      throw new Error('Não foi possível conectar ao servidor. Verifique se ele está disponível e tente novamente.');
    }
    if (response.status === 401) { logout(); throw new Error('Entre novamente.'); }
    if (response.status === 402) throw new Error('Regularize sua assinatura em Gerenciar assinatura.');
    const data = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(typeof data.detail === 'string' ? data.detail : 'Verifique os dados do perfil.');
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function run(operation) {
    if (busy) return;
    busy = true;
    status.textContent = '';
    document.querySelectorAll('.profiles-main button').forEach(button => { button.disabled = true; });
    try { await operation(); }
    catch (error) { status.textContent = error.message; }
    finally {
      busy = false;
      document.querySelectorAll('.profiles-main button').forEach(button => { button.disabled = false; });
      add_button.disabled = profiles.length === 0 || profiles.length >= 4;
    }
  }

  function owner_password(reason) {
    const dialog = document.querySelector('#owner-dialog');
    const password = document.querySelector('#owner-password');
    document.querySelector('#owner-reason').textContent = reason;
    password.value = '';
    return new Promise(resolve => {
      let result = null;
      document.querySelector('#owner-form').onsubmit = event => {
        event.preventDefault();
        result = password.value;
        dialog.close();
      };
      document.querySelector('#owner-cancel').onclick = () => dialog.close();
      dialog.addEventListener('close', () => {
        password.value = '';
        resolve(result);
      }, {once: true});
      dialog.showModal();
      password.focus();
    });
  }

  async function refresh() {
    [profiles, genres, selection] = await Promise.all([
      request('/profiles'), request('/genres'), request('/profiles/current')
    ]);
    QuaseflixSession.setProfile(selection.profile);
    render();
  }

  function button(text, action) {
    const element = document.createElement('button');
    element.type = 'button';
    element.className = 'btn';
    element.textContent = text;
    element.onclick = () => run(action);
    return element;
  }

  function render() {
    document.querySelector('#retry').hidden = true;
    document.querySelector('#profile-count').textContent = `${profiles.length} de 4 perfis`;
    document.querySelector('#selected-profile').textContent = selection.profile
      ? `Perfil selecionado: ${selection.profile.name}${selection.restricted ? ' — modo infantil' : ''}`
      : selection.restricted ? 'Escolha um perfil. O modo infantil continua protegido.' : 'Selecione um perfil para continuar.';
    const container = document.querySelector('#profile-list');
    container.replaceChildren();
    for (const profile of profiles) {
      const card = document.createElement('article');
      card.className = `profile-card${profile.is_kids ? ' kids' : ''}${selection.profile?.id === profile.id ? ' selected' : ''}`;
      const avatar = document.createElement('div');
      avatar.className = 'profile-avatar';
      avatar.textContent = profile.name.slice(0, 1).toUpperCase();
      avatar.setAttribute('aria-hidden', 'true');
      const name = document.createElement('h2');
      name.textContent = profile.name;
      const label = document.createElement('p');
      label.textContent = profile.is_kids ? 'Infantil' : 'Padrão';
      const preferences = document.createElement('p');
      preferences.className = 'muted';
      preferences.textContent = genres.filter(genre => profile.genre_ids.includes(genre.id)).map(genre => genre.name).join(', ') || 'Sem gêneros favoritos';
      card.append(avatar, name, label, preferences);
      const actions = document.createElement("div");
      actions.className = "profile-actions";
      card.append(actions);
      actions.append(button('Selecionar', async () => {
        // Refresh protection state first; the server independently checks it again.
        selection = await request('/profiles/current');
        const password = selection.restricted && !profile.is_kids
          ? await owner_password('Confirme sua senha para sair do modo infantil.') : undefined;
        if (password === null) return;
        await request(`/profiles/${profile.id}/select`, 'POST', {password});
        editor.hidden = true;
        await refresh();
      }));
      actions.append(button('Editar', async () => open_editor(profile)));
      actions.append(button('Excluir', async () => {
        if (profiles.length <= 1) throw new Error('Mantenha pelo menos um perfil.');
        if (!confirm(`Excluir o perfil “${profile.name}” e suas preferências?`)) return;
        selection = await request('/profiles/current');
        const password = selection.restricted ? await owner_password('Confirme sua senha para excluir um perfil no modo infantil.') : undefined;
        if (password === null) return;
        await request(`/profiles/${profile.id}`, 'DELETE', {password});
        editor.hidden = true;
        await refresh();
      }));
      container.append(card);
    }
  }

  function open_editor(profile = null) {
    editing = profile;
    form.reset();
    document.querySelector('#editor-title').textContent = profile ? 'Editar perfil' : 'Novo perfil';
    document.querySelector('#profile-name').value = profile?.name || '';
    document.querySelector('#profile-kids').checked = profile?.is_kids || false;
    const options = document.querySelector('#genres');
    options.replaceChildren();
    for (const genre of genres) {
      const label = document.createElement('label');
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.name = 'genre_ids';
      input.value = genre.id;
      input.checked = profile?.genre_ids.includes(genre.id) || false;
      label.append(input, document.createTextNode(` ${genre.name}`));
      options.append(label);
    }
    editor.hidden = false;
    document.querySelector('#profile-name').focus();
  }

  add_button.onclick = () => run(async () => open_editor());
  document.querySelector('#close-editor').onclick = () => { editor.hidden = true; };
  form.onsubmit = event => {
    event.preventDefault();
    run(async () => {
      selection = await request('/profiles/current');
      const data = new FormData(form);
      const payload = {
        name: data.get('name'), is_kids: data.has('is_kids'),
        genre_ids: data.getAll('genre_ids').map(Number)
      };
      if (selection.restricted || (editing?.is_kids && !payload.is_kids)) {
        payload.password = await owner_password('Confirme sua senha para alterar os perfis protegidos.');
        if (payload.password === null) return;
      }
      await request(editing ? `/profiles/${editing.id}` : '/profiles', editing ? 'PUT' : 'POST', payload);
      editor.hidden = true;
      await refresh();
    });
  };
  async function load() {
    try { await refresh(); }
    catch (error) {
      document.querySelector('#selected-profile').textContent = 'Não foi possível carregar os perfis.';
      document.querySelector('#retry').hidden = false;
      throw error;
    }
  }
  document.querySelector('#retry').onclick = () => run(load);
  run(load);
});
