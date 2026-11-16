document.addEventListener("DOMContentLoaded", () => {
  const token = QuaseflixSession.getToken();
  if (!token) {
    window.location.href = "./login.html";
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const mediaId = params.get("id");
  const episodeId = params.get("episode_id");
  const validId = value => /^[1-9]\d*$/.test(value || "");
  const status = document.getElementById("player-status");
  const content = document.getElementById("player-content");
  const video = document.getElementById("video");
  const audio = document.getElementById("audio-language");
  const subtitles = document.getElementById("subtitle-language");
  const trackStatus = document.getElementById("track-status");
  const settings = document.getElementById("playback-settings");
  const settingsButton = document.getElementById("toggle-settings");
  const subscriptionLink = document.getElementById("subscription-link");
  let session;
  let adaptivePlayer;
  let lastSavedAt = 0;
  let saveInFlight = false;

  const logout = () => {
    QuaseflixSession.clear();
    window.location.href = "./login.html";
  };
  document.getElementById("btn-logout").addEventListener("click", logout);

  if (!validId(mediaId) || (episodeId && !validId(episodeId))) {
    status.textContent = "Conteúdo inválido. Volte ao catálogo e selecione uma obra.";
    return;
  }
  document.getElementById("back-to-title").href = `./media.html?id=${mediaId}`;

  const endpoint = (progress = false) => {
    const query = episodeId ? `?episode_id=${episodeId}` : "";
    return `http://localhost:8000/api/streaming/${mediaId}${progress ? "/progress" : ""}${query}`;
  };

  const explainFailure = async response => {
    if (response.status === 401) {
      logout();
      return "Sua sessão expirou.";
    }
    if ([402, 403].includes(response.status)) {
      subscriptionLink.hidden = false;
      return "A assinatura não está ativa. Acesse Minha conta para regularizar ou reativar o plano.";
    }
    if (response.status === 409) return "Selecione um perfil ou episódio antes de assistir.";
    if (response.status === 404) return "Este conteúdo não está disponível para o perfil selecionado.";
    try { return (await response.json()).detail || "Não foi possível iniciar a reprodução."; }
    catch { return "Não foi possível iniciar a reprodução."; }
  };

  const applyAudio = language => {
    if (adaptivePlayer) {
      const track = adaptivePlayer.getVariantTracks().find(item =>
        item.language === language || item.label === language);
      if (track) {
        adaptivePlayer.selectAudioLanguage(track.language, track.role || "");
        trackStatus.textContent = `Áudio alterado para ${language}.`;
      } else {
        trackStatus.textContent = "A faixa escolhida não está presente no manifesto.";
      }
      return;
    }
    const tracks = video.audioTracks;
    if (!tracks || !tracks.length) {
      trackStatus.textContent = "A faixa será aplicada pelo manifesto de streaming quando suportada pelo navegador.";
      return;
    }
    let found = false;
    for (const track of tracks) {
      const selected = track.language === language || track.label === language;
      track.enabled = selected;
      found ||= selected;
    }
    trackStatus.textContent = found ? `Áudio alterado para ${language}.` : "A faixa escolhida não foi exposta pelo navegador.";
  };

  const applySubtitle = language => {
    if (adaptivePlayer) {
      if (!language) {
        adaptivePlayer.setTextTrackVisibility(false);
        trackStatus.textContent = "Legendas desativadas.";
        return;
      }
      const track = adaptivePlayer.getTextTracks().find(item =>
        item.language === language || item.label === language);
      if (track) {
        adaptivePlayer.selectTextTrack(track);
        adaptivePlayer.setTextTrackVisibility(true);
        trackStatus.textContent = `Legenda alterada para ${language}.`;
      } else {
        trackStatus.textContent = "A faixa escolhida não está presente no manifesto.";
      }
      return;
    }
    let found = !language;
    for (const track of video.textTracks) {
      const selected = Boolean(language) && (track.language === language || track.label === language);
      track.mode = selected ? "showing" : "disabled";
      found ||= selected;
    }
    trackStatus.textContent = found
      ? language ? `Legenda alterada para ${language}.` : "Legendas desativadas."
      : "A faixa escolhida não foi exposta pelo navegador.";
  };

  const progressBody = () => ({
    position_seconds: Math.min(Number.isFinite(video.currentTime) ? video.currentTime : 0, session.duration_seconds),
    audio_language: audio.value || null,
    subtitle_language: subtitles.value || null,
  });

  const saveProgress = async (keepalive = false) => {
    if (!session || saveInFlight && !keepalive) return;
    saveInFlight = true;
    try {
      await fetch(endpoint(true), {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(progressBody()),
        keepalive,
      });
      lastSavedAt = Date.now();
    } finally {
      saveInFlight = false;
    }
  };

  settingsButton.addEventListener("click", () => {
    settings.hidden = !settings.hidden;
    settingsButton.setAttribute("aria-expanded", String(!settings.hidden));
  });
  audio.addEventListener("change", () => { applyAudio(audio.value); saveProgress(); });
  subtitles.addEventListener("change", () => { applySubtitle(subtitles.value); saveProgress(); });
  video.addEventListener("timeupdate", () => {
    if (Date.now() - lastSavedAt >= 10000) saveProgress();
  });
  video.addEventListener("pause", () => saveProgress());
  video.addEventListener("ended", () => saveProgress());
  window.addEventListener("pagehide", () => {
    saveProgress(true);
    adaptivePlayer?.destroy();
  });

  const load = async () => {
    try {
      const response = await fetch(endpoint(), { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error(await explainFailure(response));
      session = await response.json();
      document.title = `${session.episode_title || session.title} | QuaseFlix`;
      document.getElementById("content-kind").textContent = session.content_type === "movie" ? "Filme" : session.title;
      document.getElementById("content-title").textContent = session.episode_title || session.title;

      audio.replaceChildren();
      const audioTracks = session.audio_tracks.length ? session.audio_tracks : [{ language: "Original" }];
      for (const track of audioTracks) {
        const option = document.createElement("option");
        option.value = session.audio_tracks.length ? track.language : "";
        option.textContent = track.language;
        audio.append(option);
      }
      if (session.selected_audio && audioTracks.some(track => track.language === session.selected_audio)) {
        audio.value = session.selected_audio;
      }
      for (const track of session.subtitle_tracks) {
        const option = document.createElement("option");
        option.value = option.textContent = track.language;
        subtitles.append(option);
      }
      if (session.selected_subtitle && session.subtitle_tracks.some(track => track.language === session.selected_subtitle)) {
        subtitles.value = session.selected_subtitle;
      }

      const restorePlayback = () => {
        if (session.resume_position_seconds > 0 && session.resume_position_seconds < video.duration) {
          video.currentTime = session.resume_position_seconds;
          status.textContent = `Reprodução retomada em ${Math.floor(session.resume_position_seconds / 60)} min ${Math.floor(session.resume_position_seconds % 60)} s.`;
        }
        applyAudio(audio.value);
        applySubtitle(subtitles.value);
      };
      video.addEventListener("error", () => {
        status.textContent = "A fonte de vídeo não pôde ser carregada. Verifique o endereço da CDN e o formato do manifesto.";
      });
      content.hidden = false;
      await (window.QuaseflixShakaReady || Promise.resolve(false));
      if (session.adaptive && window.shaka) {
        shaka.polyfill.installAll();
        if (!shaka.Player.isBrowserSupported()) throw new Error("Este navegador não oferece os recursos necessários para streaming adaptativo.");
        adaptivePlayer = new shaka.Player();
        await adaptivePlayer.attach(video);
        adaptivePlayer.configure({ abr: { enabled: true } });
        await adaptivePlayer.load(session.stream_url);
        restorePlayback();
        status.textContent = session.resume_position_seconds > 0
          ? status.textContent : "Qualidade adaptativa habilitada para esta transmissão.";
      } else {
        const source = document.createElement("source");
        source.src = session.stream_url;
        source.type = session.stream_type;
        video.replaceChildren(source);
        video.addEventListener("loadedmetadata", restorePlayback, { once: true });
        status.textContent = session.adaptive
          ? "O player adaptativo não pôde ser carregado; usando o suporte nativo do navegador."
          : "Reprodução pronta.";
        video.load();
      }
    } catch (error) {
      status.textContent = error instanceof TypeError ? "Não foi possível conectar ao servidor." : error.message;
    }
  };
  load();
});
