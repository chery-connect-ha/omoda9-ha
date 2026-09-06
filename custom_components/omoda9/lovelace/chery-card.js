/*
 * Chery vehicle card — sleek summary (Omoda 9 / Chery / Jaecoo integration).
 *
 * At-a-glance: vehicle photo, name, battery %, estimated range, charging state, and
 * warnings (tyre / low battery / offline) shown only when something's wrong.
 * Auto-discovers this integration's entities, so minimal config just works:
 *   type: custom:chery-card
 * Options:
 *   title: "My Car"          # header title (default: the vehicle's name)
 *   image: "/local/car.png"  # header photo (overrides the one set in the integration options)
 *   show_all: true           # also list every remaining entity, grouped
 *   entities: [...]          # append your own rows (entity ids)
 *   integration: "omoda9"    # platform to collect (default)
 *   prefix: "omoda9_"        # object_id fallback prefix
 */
class CheryCard extends HTMLElement {
  setConfig(config) {
    this.config = Object.assign(
      { integration: "omoda9", prefix: "omoda9_", show_all: false },
      config || {}
    );
  }
  getCardSize() { return 4; }

  _dead(s) { return !s || ["unavailable", "unknown", ""].includes(s.state); }
  _num(s) { const n = s ? parseFloat(s.state) : NaN; return isNaN(n) ? null : n; }
  // Display a value the way Home Assistant would: respects the entity's display precision
  // (so "145.4008… mi" shows as "145 mi" if you set 0 decimals) and unit conversion.
  _disp(s) {
    const h = this._hass;
    if (h && typeof h.formatEntityState === "function") {
      try { return h.formatEntityState(s); } catch (e) { /* fall through */ }
    }
    const n = parseFloat(s.state);
    const u = s.attributes.unit_of_measurement;
    if (isNaN(n)) return u ? `${s.state} ${u}` : s.state;
    const dp = s.attributes.suggested_display_precision;
    const v = typeof dp === "number" ? n.toFixed(dp) : (Number.isInteger(n) ? `${n}` : `${Math.round(n)}`);
    return u ? `${v} ${u}` : v;
  }

  _collect(hass) {
    const c = this.config, out = [];
    const strip = (o) => o.startsWith(c.prefix) ? o.slice(c.prefix.length) : o;
    const reg = hass.entities;
    if (reg) for (const id in reg) {
      if (reg[id].platform !== c.integration) continue;
      const s = hass.states[id]; if (s) out.push({ id, key: strip(id.slice(id.indexOf(".") + 1)), s });
    }
    if (!out.length) for (const id in hass.states) {
      const o = id.slice(id.indexOf(".") + 1);
      if (o.startsWith(c.prefix)) out.push({ id, key: strip(o), s: hass.states[id] });
    }
    return out;
  }

  _find(items, ...keys) {
    for (const k of keys) { const f = items.find((r) => r.key === k); if (f) return f; }
    return null;
  }
  // Escape a string for safe use inside `new RegExp(...)` (vehicle names can contain
  // regex-special chars like ( ) + . which would otherwise throw during render).
  _esc(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
  // Escape for an HTML text/attribute context. The card builds its DOM from vehicle- and
  // backend-supplied strings (vehicle name, image URL, entity states, warnings) via innerHTML,
  // so EVERY interpolated value must be neutralised to prevent HTML/script injection (XSS).
  _h(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }
  // Sanitise a URL used inside background-image:url('…'): allow only http(s), root-relative, or
  // data:image, and percent-encode the characters that could break out of the url() or the style
  // attribute. Anything else (e.g. javascript:, data:text/html) becomes empty.
  _imgUrl(s) {
    s = String(s || "");
    if (!/^(https?:\/\/|\/|data:image\/)/i.test(s)) return "";
    return s.replace(/["'()\\<>\s]/g, encodeURIComponent);
  }

  _batteryIcon(v, charging) {
    if (charging) return "mdi:battery-charging";
    if (isNaN(v)) return "mdi:battery";
    const s = Math.round(v / 10) * 10;
    return s >= 100 ? "mdi:battery" : s <= 0 ? "mdi:battery-outline" : `mdi:battery-${s}`;
  }
  _batteryColor(v) {
    if (isNaN(v)) return "var(--primary-text-color)";
    if (v <= 15) return "#e5484d";
    if (v <= 30) return "#f5a623";
    return "#3dd68c";
  }
  _moreInfo(id) {
    this.dispatchEvent(new CustomEvent("hass-more-info",
      { bubbles: true, composed: true, detail: { entityId: id } }));
  }
  _deviceId(hass, items) {
    const reg = hass.entities;
    if (!reg) return null;
    for (const { id } of items) { const d = reg[id] && reg[id].device_id; if (d) return d; }
    return null;
  }
  _navigate(path) {
    history.pushState(null, "", path);
    this.dispatchEvent(new Event("location-changed", { bubbles: true, composed: true }));
  }

  set hass(hass) {
    this._hass = hass;
    if (!this.content) {
      const card = document.createElement("ha-card");
      const style = document.createElement("style");
      style.textContent = `
        ha-card { overflow: hidden; }
        .hero { position: relative; min-height: 132px; display: flex; align-items: flex-end;
          /* solid fallback first: iOS/Safari & old webviews that don't support color-mix()
             keep a usable background instead of a blank hero. */
          background-color: var(--primary-color);
          background-image: linear-gradient(135deg, var(--primary-color) 0%, color-mix(in srgb, var(--primary-color) 55%, #000) 100%);
          background-size: cover; background-position: center; }
        .hero.photo { min-height: 190px; }
        .scrim { position: absolute; inset: 0;
          background: linear-gradient(to top, rgba(0,0,0,.66) 0%, rgba(0,0,0,.15) 55%, rgba(0,0,0,0) 100%); }
        .hero-content { position: relative; width: 100%; padding: 16px; display: flex;
          align-items: flex-end; justify-content: space-between; gap: 12px; color: #fff; }
        .name { font-size: 1.35rem; font-weight: 700; line-height: 1.15; text-shadow: 0 1px 4px rgba(0,0,0,.55); }
        .sub { font-size: .82rem; opacity: .9; margin-top: 2px; text-shadow: 0 1px 3px rgba(0,0,0,.5);
          display: flex; align-items: center; gap: 6px; }
        .sub ha-icon { --mdc-icon-size: 16px; }
        .batt { display: flex; align-items: center; gap: 7px; padding: 7px 12px; cursor: pointer;
          background: rgba(0,0,0,.32); border-radius: 999px;
          -webkit-backdrop-filter: blur(6px); backdrop-filter: blur(6px); }
        .batt ha-icon { --mdc-icon-size: 22px; }
        .batt b { font-size: 1.15rem; font-weight: 700; }
        .metrics { display: flex; }
        .metric { flex: 1; padding: 13px 14px; cursor: pointer; text-align: center;
          border-right: 1px solid var(--divider-color, rgba(127,127,127,.18)); }
        .metric:last-child { border-right: none; }
        .metric:hover { background: var(--secondary-background-color); }
        .metric .v { font-size: 1.1rem; font-weight: 700; color: var(--primary-text-color); }
        .metric .l { font-size: .72rem; letter-spacing: .02em; text-transform: uppercase;
          color: var(--secondary-text-color); margin-top: 3px; display: flex; align-items: center;
          justify-content: center; gap: 5px; }
        .metric .l ha-icon { --mdc-icon-size: 14px; }
        .warns { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 14px;
          border-top: 1px solid var(--divider-color, rgba(127,127,127,.18)); }
        .warn { display: flex; align-items: center; gap: 6px; font-size: .82rem; font-weight: 600;
          color: #e5484d; background: rgba(229,72,77,.13); padding: 5px 11px; border-radius: 999px; cursor: pointer; }
        .warn ha-icon { --mdc-icon-size: 15px; }
        .grp { padding: 12px 16px 2px; font-weight: 600; font-size: .85rem; color: var(--secondary-text-color);
          border-top: 1px solid var(--divider-color, rgba(127,127,127,.18)); }
        .row { display: flex; justify-content: space-between; padding: 7px 16px; cursor: pointer; font-size: .95rem; }
        .row:hover { background: var(--secondary-background-color); }
        .row .val { font-weight: 600; }
      `;
      this.content = document.createElement("div");
      card.appendChild(style); card.appendChild(this.content); this.appendChild(card);
      this.content.addEventListener("click", (e) => {
        // battery badge (data-e) opens more-info; the rest of the hero navigates to the
        // device page. Check data-e first since the badge sits inside the hero.
        const el = e.target.closest("[data-e]");
        if (el) { this._moreInfo(el.getAttribute("data-e")); return; }
        const dev = e.target.closest("[data-device]");
        if (dev && dev.getAttribute("data-device")) {
          this._navigate(`/config/devices/device/${dev.getAttribute("data-device")}`);
        }
      });
    }
    // A render exception must never bubble up as a bare "Configuration error" card —
    // show the message inline instead so the card still appears (and is debuggable).
    try {
      this._render(hass);
    } catch (e) {
      this.content.innerHTML =
        `<div style="padding:16px;color:var(--error-color,#e5484d)">Chery card error: ${e && e.message ? e.message : e}</div>`;
    }
  }

  _render(hass) {
    const cfg = this.config;
    const items = this._collect(hass);
    // NB: no optional chaining (?.) anywhere in this file — older Android System WebView
    // builds fail to PARSE it, which stops customElements.define() from ever running and
    // makes the whole card show "Configuration error" on the mobile app only.
    const nameHolder = items.find((r) => r.s.attributes.friendly_name);
    const nameSrc = nameHolder ? nameHolder.s.attributes.friendly_name : null;
    const device = nameSrc ? nameSrc.split(" ").slice(0, 2).join(" ") : "Omoda 9";
    const deviceRe = this._esc(device);
    const title = cfg.title || device;

    const bat = this._find(items, "battery") || items.find((r) =>
      r.s.attributes.device_class === "battery" && r.s.attributes.unit_of_measurement === "%");
    const range = this._find(items, "range_electric", "range_total", "range_combined_estimate");
    const chargeState = this._find(items, "charge_state");
    const charging = this._find(items, "charging");
    const plug = this._find(items, "charge_plug");
    const odo = this._find(items, "odometer");
    const isCharging = charging ? charging.s.state === "on"
      : (chargeState && /charg/i.test(chargeState.s.state) && !/not/i.test(chargeState.s.state));
    const batV = bat ? this._num(bat.s) : NaN;

    const lock = this._find(items, "lock");
    const lockText = lock && !this._dead(lock.s)
      ? (lock.s.state === "locked" ? "Locked" : "Unlocked") : "—";
    const lockIcon = lock && lock.s.state === "unlocked" ? "mdi:lock-open-variant" : "mdi:lock";

    // ---- hero (photo or gradient) — subline shows the lock status ----
    const img = cfg.image || items.map((r) => r.s.attributes.vehicle_image).find(Boolean) || "";
    const sub = isCharging
      ? `<div class="sub"><ha-icon icon="mdi:flash"></ha-icon>Charging · <ha-icon icon="${lockIcon}"></ha-icon>${this._h(lockText)}</div>`
      : `<div class="sub"><ha-icon icon="${lockIcon}"></ha-icon>${this._h(lockText)}</div>`;
    const battBadge = (bat && !this._dead(bat.s))
      ? `<div class="batt" data-e="${this._h(bat.id)}">
           <ha-icon icon="${this._batteryIcon(batV, isCharging)}" style="color:${this._batteryColor(batV)}"></ha-icon>
           <b>${isNaN(batV) ? this._h(bat.s.state) : Math.round(batV)}%</b></div>`
      : "";
    // Clicking the photo/hero opens the device page (not a control), so it can't actuate.
    const deviceId = this._deviceId(hass, items);
    const safeImg = this._imgUrl(img);
    const hero = `
      <div class="hero ${safeImg ? "photo" : ""}" style="${safeImg ? `background-image:url('${safeImg}')` : ""}"
           ${deviceId ? `data-device="${this._h(deviceId)}"` : ""}>
        <div class="scrim"></div>
        <div class="hero-content">
          <div><div class="name">${this._h(title)}</div>${sub}</div>
          ${battBadge}
        </div>
      </div>`;

    // ---- metrics strip (range · charging · odometer) ----
    // `entityId` omitted → the tile is read-only text (no more-info, no accidental action).
    const metric = (label, icon, value, entityId) => `
      <div class="metric" ${entityId ? `data-e="${this._h(entityId)}"` : ""}>
        <div class="v">${this._h(value)}</div><div class="l"><ha-icon icon="${icon}"></ha-icon>${this._h(label)}</div></div>`;
    const chargeText = charging && !this._dead(charging.s) ? (isCharging ? "Charging" : "Idle")
      : (chargeState && !this._dead(chargeState.s) ? chargeState.s.state : "—");
    const metrics = `<div class="metrics">
      ${metric("Range", "mdi:map-marker-distance", range && !this._dead(range.s) ? this._disp(range.s) : "—", range && range.id)}
      ${metric("Charging", isCharging ? "mdi:battery-charging" : "mdi:power-plug", chargeText)}
      ${odo && !this._dead(odo.s) ? metric("Odometer", "mdi:counter", this._disp(odo.s), odo.id)
        : metric("Cable", "mdi:power-plug", plug && plug.s.state === "on" ? "Plugged in" : "Unplugged")}
    </div>`;

    // ---- warnings (only active) ----
    const warns = [];
    items.filter((r) => /tire.*warning|tyre.*warning/.test(r.key) && r.s.state === "on")
      .forEach((r) => warns.push({ id: r.id, icon: "mdi:car-tire-alert",
        text: (r.s.attributes.friendly_name || r.key).replace(new RegExp("^" + deviceRe + "\\s*", "i"), "").replace(/warning/i, "").trim() }));
    const low = this._find(items, "battery_low");
    if (low && low.s.state === "on") warns.push({ id: low.id, icon: "mdi:battery-alert", text: "Battery low" });
    const conn = this._find(items, "connection");
    if (conn && conn.s.state === "off") warns.push({ id: conn.id, icon: "mdi:wifi-off", text: "Offline" });
    const warnHtml = warns.length ? `<div class="warns">${warns.map((w) =>
      `<div class="warn" data-e="${this._h(w.id)}"><ha-icon icon="${w.icon}"></ha-icon>${this._h(w.text)}</div>`).join("")}</div>` : "";

    // ---- optional extra rows / full list ----
    let extra = "";
    const used = new Set([bat, range, chargeState, charging, plug, odo, low, conn].filter(Boolean).map((r) => r.id));
    const rowFor = (id) => {
      const s = hass.states[id]; if (!s) return "";
      const name = (s.attributes.friendly_name || id).replace(new RegExp("^" + deviceRe + "\\s*", "i"), "").trim() || id;
      return `<div class="row" data-e="${this._h(id)}"><div>${this._h(name)}</div><div class="val">${this._h(this._disp(s))}</div></div>`;
    };
    if (Array.isArray(cfg.entities) && cfg.entities.length) {
      extra = `<div class="grp">Details</div>` + cfg.entities.map((e) => rowFor(typeof e === "string" ? e : e.entity)).join("");
    } else if (cfg.show_all) {
      const rest = items.filter((r) => !used.has(r.id) && !this._dead(r.s) && r.s.attributes.entity_category !== "diagnostic");
      if (rest.length) extra = `<div class="grp">More</div>` +
        rest.sort((a, b) => a.key.localeCompare(b.key)).map((r) => rowFor(r.id)).join("");
    }

    this.content.innerHTML = hero + metrics + warnHtml + extra;
  }

  static getStubConfig() { return { type: "custom:chery-card" }; }
}
// Guard against double-registration: the mobile app can evaluate this module more than
// once (auto-injected + cached), and a duplicate customElements.define() throws, which
// would abort the second load.
if (!customElements.get("chery-card")) {
  customElements.define("chery-card", CheryCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "chery-card")) {
  window.customCards.push({
    type: "chery-card",
    name: "Chery Card",
    preview: true,
    description: "Sleek summary card for the Chery/Omoda/Jaecoo integration (photo, battery, range, charging, warnings).",
  });
}
