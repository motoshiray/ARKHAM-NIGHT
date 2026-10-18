// 背景音乐和雨声。曲子都是 opengameart.org 上的 CC0：
//   Moil — Ruskerdax（首页）
//   8-bit Curious Theme — emanresU（桌上默认）
//   Contemplation — Joth（桌上可选）
//   Dark Rainy Night (ambience) — kindland（雨声）
// 默认都关着。浏览器规定声音要由一次点击触发，所以「开着」的偏好会在下一次点击时生效。
(function () {
  const TRACKS = {
    moil: { src: "/assets/bgm-moil.mp3", gain: 0.45, name: "Moil" },
    curious: { src: "/assets/bgm-curious.ogg", gain: 0.3, name: "8-bit Curious Theme" },
    contemplation: { src: "/assets/bgm-contemplation.mp3", gain: 0.5, name: "Contemplation" },
  };
  const RAIN = { src: "/assets/amb-rain.ogg", gain: 0.55 };

  const get = (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } };
  const set = (k, v) => { try { localStorage.setItem(k, String(v)); } catch (e) {} };

  let page = "table", music = null, rain = null;
  const st = {
    music: get("arkham-night-music", "off") === "on",
    rain: get("arkham-night-rain", "off") === "on",
    vol: parseFloat(get("arkham-night-vol", "0.6")) || 0.6,
    track: get("arkham-night-track", "curious"),
  };
  if (!TRACKS[st.track] || st.track === "moil") st.track = "curious";
  let playing = { music: false, rain: false };
  const listeners = [];
  const notify = () => listeners.forEach((f) => f({ ...st, playing: { ...playing } }));

  function audio(src) { const a = new Audio(src); a.loop = true; a.preload = "none"; a.volume = 0; return a; }
  function fade(a, to, ms, done) {
    clearInterval(a._fade);
    const from = a.volume, t0 = performance.now();
    a._fade = setInterval(() => {
      const k = Math.min(1, (performance.now() - t0) / ms);
      a.volume = Math.max(0, Math.min(1, from + (to - from) * k));
      if (k >= 1) { clearInterval(a._fade); done && done(); }
    }, 40);
  }
  const musicKey = () => (page === "home" ? "moil" : st.track);
  const musicTarget = () => TRACKS[musicKey()].gain * st.vol;

  function playMusic() {
    const key = musicKey();
    if (music && music._key !== key) { const old = music; fade(old, 0, 600, () => old.pause()); music = null; }
    if (!music) { music = audio(TRACKS[key].src); music._key = key; }
    music.play().then(() => { playing.music = true; notify(); }).catch(() => {});
    fade(music, musicTarget(), 1500);
  }
  function stopMusic() { if (music) { const m = music; fade(m, 0, 600, () => m.pause()); } playing.music = false; notify(); }
  function playRain() {
    if (!rain) rain = audio(RAIN.src);
    rain.play().then(() => { playing.rain = true; notify(); }).catch(() => {});
    fade(rain, RAIN.gain * st.vol, 1500);
  }
  function stopRain() { if (rain) { const r = rain; fade(r, 0, 600, () => r.pause()); } playing.rain = false; notify(); }

  function resume() { if (st.music) playMusic(); if (st.rain) playRain(); }

  window.Ambient = {
    tracks: TRACKS,
    init(p) {
      page = p;
      if (st.music || st.rain) {
        const once = (e) => {
          document.removeEventListener("pointerdown", once, true);
          if (!(e.target.closest && e.target.closest("[data-ambient]"))) resume(); // 点的就是开关的话，交给开关自己
        };
        document.addEventListener("pointerdown", once, true);
      }
      notify();
    },
    toggleMusic() { st.music = !playing.music; set("arkham-night-music", st.music ? "on" : "off"); st.music ? playMusic() : stopMusic(); },
    toggleRain() { st.rain = !playing.rain; set("arkham-night-rain", st.rain ? "on" : "off"); st.rain ? playRain() : stopRain(); },
    stopAll() { stopMusic(); stopRain(); },
    setVolume(v) {
      st.vol = v; set("arkham-night-vol", v);
      if (music && playing.music) fade(music, musicTarget(), 200);
      if (rain && playing.rain) fade(rain, RAIN.gain * v, 200);
      notify();
    },
    setTrack(key) {
      if (!TRACKS[key] || key === "moil") return;
      st.track = key; set("arkham-night-track", key);
      if (page === "table" && playing.music) playMusic();
      notify();
    },
    state: () => ({ ...st, playing: { ...playing } }),
    onChange(f) { listeners.push(f); },
  };
})();
