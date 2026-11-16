document.addEventListener("DOMContentLoaded", () => {
  if (!CatalogAPI.initialize()) return;
  const { element } = CatalogAPI;
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");
  params.delete("id");
  document.getElementById("back-to-catalog").href = `./catalog.html?${params}`;
  const status = document.getElementById("media-status");
  const retry = document.getElementById("retry");
  const details = document.getElementById("media-details");
  const metadata = document.getElementById("metadata");
  const addMetadata = (label, value) => {
    metadata.append(element("dt", label), element("dd", value));
  };
  const list = (values, empty = "Não informado") => values.length ? values.join(", ") : empty;

  const load = async () => {
    if (!/^[1-9]\d*$/.test(id || "")) {
      status.textContent = "Obra inválida. Volte ao catálogo e selecione um título.";
      return;
    }
    retry.hidden = true;
    status.textContent = "Carregando detalhes…";
    try {
      const media = await CatalogAPI.get(`/${id}`);
      document.title = `${media.title} | QuaseFlix`;
      document.getElementById("media-type").textContent = media.media_type === "movie" ? "Filme" : "Série";
      document.getElementById("media-title").textContent = media.title;
      document.getElementById("media-synopsis").textContent = media.synopsis || "Sinopse não informada.";
      const watch = document.getElementById("watch-media");
      watch.hidden = media.media_type !== "movie";
      watch.href = `./player.html?id=${media.id}`;
      metadata.replaceChildren();
      addMetadata("Ano de produção", media.release_year ?? "Não informado");
      addMetadata("Gêneros", list(media.genres));
      addMetadata(media.media_type === "movie" ? "Duração" : "Duração total dos episódios", `${media.duration_minutes} min`);
      addMetadata("Elenco", list(media.actors));
      addMetadata("Direção", list(media.directors));
      addMetadata("Áudios disponíveis", list(media.audio_languages));
      addMetadata("Legendas disponíveis", list(media.subtitle_languages, "Nenhuma legenda disponível"));
      const seasons = document.getElementById("seasons");
      const seasonItems = document.getElementById("season-items");
      seasonItems.replaceChildren();
      seasons.hidden = media.media_type !== "series";
      if (!seasons.hidden) {
        addMetadata("Temporadas", media.season_count);
        addMetadata("Episódios", media.episode_count);
        if (!media.seasons.length) seasonItems.append(element("p", "Nenhuma temporada cadastrada."));
        media.seasons.forEach(season => {
          const section = element("section", undefined, "season");
          section.append(element("h3", `Temporada ${season.season_number}${season.title ? ` — ${season.title}` : ""}`));
          if (!season.episodes.length) section.append(element("p", "Nenhum episódio cadastrado."));
          const episodes = element("ol", undefined, "episode-list");
          season.episodes.forEach(episode => {
            const item = element("li");
            item.value = episode.episode_number;
            item.append(element("h4", episode.title),
              element("p", `${episode.duration_minutes} min · Direção: ${episode.director || "Não informada"}`, "muted"));
            const play = element("a", "Assistir episódio", "btn btn-primary btn-sm");
            play.href = `./player.html?id=${media.id}&episode_id=${episode.id}`;
            item.append(play);
            episodes.append(item);
          });
          section.append(episodes);
          seasonItems.append(section);
        });
      }
      status.textContent = "";
      details.hidden = false;
    } catch (error) {
      status.textContent = error instanceof TypeError ? "Não foi possível conectar ao servidor." : error.message;
      retry.hidden = error.status === 404;
    }
  };
  retry.addEventListener("click", load);
  load();
});
