import { useState, useMemo, useEffect } from "react";
import ROSTERS from "../bleague-rosters.json";
import PLAYER_CLUSTERS from "../player_clusters.json";

const POS_COLOR = { PG: "#3B82F6", SG: "#8B5CF6", SF: "#10B981", PF: "#F97316", C: "#EF4444" };
const NAT_FLAG = {
  Japan: "🇯🇵", USA: "🇺🇸", Korea: "🇰🇷", Australia: "🇦🇺", France: "🇫🇷",
  Canada: "🇨🇦", Taiwan: "🇹🇼", "New Zealand": "🇳🇿", Nigeria: "🇳🇬",
  Lithuania: "🇱🇹", Serbia: "🇷🇸", Montenegro: "🇲🇪", Croatia: "🇭🇷", Brazil: "🇧🇷",
  Philippines: "🇵🇭", Germany: "🇩🇪", Spain: "🇪🇸", Italy: "🇮🇹", China: "🇨🇳",
  "Puerto Rico": "🇵🇷", Panama: "🇵🇦", Venezuela: "🇻🇪", Slovenia: "🇸🇮",
  Poland: "🇵🇱", Georgia: "🇬🇪", UK: "🇬🇧", Mexico: "🇲🇽", Argentina: "🇦🇷",
  Greece: "🇬🇷", Finland: "🇫🇮", Senegal: "🇸🇳", Bahamas: "🇧🇸",
};

const CONFERENCES = {
  east: {
    label: "동부",
    order: [
      "utsunomiya", "chiba_jets", "gunma", "alvark_tokyo", "levanga", "sendai",
      "yokohama", "sun_rockers", "koshigaya", "altiri_chiba", "ibaraki", "kawasaki", "akita",
    ],
  },
  west: {
    label: "서부",
    order: [
      "nagasaki", "mikawa", "ryukyu", "nagoya_dd", "sanen", "saga", "hiroshima", "shimane",
      "osaka", "shiga", "kyoto", "toyama", "fighting_eagles",
      "shinshu", "kobe",
    ],
  },
};

const SORTS = {
  avg_min: { label: "평균 시간", timeKey: "minutes_avg", secKey: "minutes_avg_sec", desc: true },
  total_min: { label: "총 시간", timeKey: "minutes_total", secKey: "minutes_total_sec", desc: true },
  number: { label: "등번호", secKey: "number", desc: false },
  name: { label: "이름", secKey: "name_korean", desc: false },
};

function teamList(conf) {
  const order = CONFERENCES[conf].order;
  return order
    .filter((id) => ROSTERS.teams[id])
    .map((id) => ({ id, conference: conf, ...ROSTERS.teams[id] }));
}

function hexLuminance(hex) {
  if (!hex || !hex.startsWith("#") || hex.length < 7) return 1;
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

const TEAM_CARD_HIGHLIGHT = {
  gunma: "#38BDF8",
  utsunomiya: "#FDB913",
  toyama: "#FF6600",
};

function cardHighlight(team) {
  if (team.id && TEAM_CARD_HIGHLIGHT[team.id]) {
    return TEAM_CARD_HIGHLIGHT[team.id];
  }
  const accent = team.accent || team.primary || "#F59E0B";
  return hexLuminance(accent) < 0.15 ? (team.primary || "#F59E0B") : accent;
}

const STARTER_COUNT = 5;
const BENCH_COUNT = 4;
const ROTATION_COUNT = STARTER_COUNT + BENCH_COUNT;
const MIN_GAMES = 5;

function rankBy(players, key) {
  const sorted = [...players].sort((a, b) => (b[key] || 0) - (a[key] || 0));
  const ranks = {};
  sorted.forEach((p, i) => { ranks[p.player_id] = i + 1; });
  return ranks;
}

function rankedCorePlayers(players) {
  const pool = players.filter(
    (p) => (p.games || 0) >= MIN_GAMES || (p.minutes_avg_sec || 0) > 0,
  );
  if (!pool.length) return [];

  const hasGs = pool.some((p) => (p.games_started || 0) > 0);
  if (!hasGs) {
    return [...pool]
      .sort((a, b) => (b.minutes_avg_sec || 0) - (a.minutes_avg_sec || 0))
      .slice(0, ROTATION_COUNT)
      .map((p) => p.player_id);
  }

  const gsRank = rankBy(pool, "games_started");
  const minRank = rankBy(pool, "minutes_avg_sec");
  return pool
    .map((p) => ({
      id: p.player_id,
      score: (gsRank[p.player_id] || 99) + (minRank[p.player_id] || 99),
    }))
    .sort((a, b) => a.score - b.score || a.id.localeCompare(b.id))
    .slice(0, ROTATION_COUNT)
    .map((x) => x.id);
}

function coreRotation(players) {
  const ranked = rankedCorePlayers(players);
  return {
    starterIds: new Set(ranked.slice(0, STARTER_COUNT)),
    benchIds: new Set(ranked.slice(STARTER_COUNT, ROTATION_COUNT)),
  };
}

function sortPlayers(players, sortBy) {
  const cfg = SORTS[sortBy];
  const list = [...players];
  list.sort((a, b) => {
    if (sortBy === "number") {
      const an = parseInt(a.number, 10) || 999;
      const bn = parseInt(b.number, 10) || 999;
      return an - bn;
    }
    if (sortBy === "name") {
      return (a.name_korean || "").localeCompare(b.name_korean || "", "ko");
    }
    const av = a[cfg.secKey] || 0;
    const bv = b[cfg.secKey] || 0;
    return cfg.desc ? bv - av : av - bv;
  });
  return list;
}

function JerseyFallback({ number, primary, accent }) {
  return (
    <div style={{ width: "100%", height: "100%", background: primary, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <span style={{ color: accent, fontSize: "50px", fontWeight: 900, fontFamily: "'Arial Black',Arial,sans-serif" }}>{number || "?"}</span>
    </div>
  );
}

function PlayerCard({ player, team, idx, sortBy, role }) {
  const [imgErr, setImgErr] = useState(false);
  const [show, setShow] = useState(false);
  useEffect(() => { const t = setTimeout(() => setShow(true), idx * 35); return () => clearTimeout(t); }, [idx]);
  const pc = POS_COLOR[player.position] || "#6B7280";
  const flag = NAT_FLAG[player.nationality] || "🌍";
  const hasPhoto = player.photo_url && !imgErr;
  const timeVal = sortBy === "total_min"
    ? (player.minutes_total || "-")
    : (player.minutes_avg || "-");
  const pos = player.position || "-";
  const hi = cardHighlight(team);
  const clusterName = PLAYER_CLUSTERS.by_player_id?.[player.player_id] || "";
  const headerLabel = clusterName || team.name_korean;

  const cardStyle = (() => {
    if (role === "starter") {
      return {
        border: `5px solid ${hi}`,
        boxShadow: `0 0 32px ${hi}, 0 0 64px ${hi}88`,
      };
    }
    if (role === "bench") {
      return {
        border: `2px dashed ${hi}`,
        boxShadow: "none",
      };
    }
    return { border: "1px solid #1E293B", boxShadow: "none" };
  })();

  return (
    <a href={player.profile_url} target="_blank" rel="noopener noreferrer" style={{
      borderRadius: "10px", overflow: "hidden", textDecoration: "none", background: "#0F172A", border: cardStyle.border,
      boxShadow: cardStyle.boxShadow,
      display: "flex", flexDirection: "column", opacity: show ? 1 : 0, transform: show ? "translateY(0)" : "translateY(14px)",
      transition: "opacity .28s, transform .28s, border .2s, box-shadow .2s", cursor: "pointer",
    }} onMouseEnter={(e) => {
      if (role === "starter") e.currentTarget.style.boxShadow = `0 0 36px ${hi}cc, 0 0 64px ${hi}55`;
    }}
       onMouseLeave={(e) => {
         e.currentTarget.style.border = cardStyle.border;
         e.currentTarget.style.boxShadow = cardStyle.boxShadow;
       }}>
      <div style={{ background: team.primary, padding: "6px 10px", display: "flex", alignItems: "center", gap: "8px", borderBottom: `2px solid ${team.accent}55`, minHeight: clusterName ? "40px" : undefined }}>
        <img src={team.logo_url} alt="" style={{ width: 22, height: 22, objectFit: "contain", flexShrink: 0 }} />
        <span style={{
          color: team.accent,
          fontSize: clusterName ? "10px" : "11px",
          fontWeight: 700,
          flex: 1,
          lineHeight: 1.25,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }} title={headerLabel}>{headerLabel}</span>
        <span style={{ color: team.accent, fontSize: "12px", fontWeight: 800, flexShrink: 0 }}>#{player.number}</span>
      </div>
      <div style={{ height: "172px", overflow: "hidden", background: "#0a0f1a" }}>
        {hasPhoto ? (
          <img src={player.photo_url} alt={player.name_korean} loading="lazy" onError={() => setImgErr(true)}
            style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "top center" }} />
        ) : (
          <JerseyFallback number={player.number} primary={team.primary} accent={team.accent} />
        )}
      </div>
      <div style={{ padding: "10px 10px 11px", borderTop: `1px solid ${team.primary}33` }}>
        <div style={{ color: "#F1F5F9", fontSize: "14px", fontWeight: 600, lineHeight: 1.35 }}>
          {player.name_korean}
          <span style={{ color: pc, fontSize: "12px", fontWeight: 700, marginLeft: "4px" }}>
            ({pos} · {timeVal})
          </span>
        </div>
        <div style={{ marginTop: "4px", fontSize: "11px", color: "#64748B" }}>{flag} {player.name_en || ""}</div>
        {role === "starter" && (
          <div style={{ marginTop: "6px", fontSize: "10px", fontWeight: 800, color: hi, letterSpacing: "0.04em" }}>주전</div>
        )}
        {role === "bench" && (
          <div style={{ marginTop: "6px", fontSize: "10px", fontWeight: 700, color: `${hi}aa`, letterSpacing: "0.04em" }}>벤치</div>
        )}
      </div>
    </a>
  );
}

export default function RosterPage() {
  const [conf, setConf] = useState("west");
  const [sortBy, setSortBy] = useState("avg_min");
  const teams = useMemo(() => teamList(conf), [conf]);
  const [selId, setSelId] = useState("nagasaki");

  useEffect(() => {
    const list = teamList(conf);
    const fallback = conf === "west" ? "nagasaki" : list[0]?.id;
    setSelId((prev) => {
      if (list.some((t) => t.id === prev)) return prev;
      if (fallback && list.some((t) => t.id === fallback)) return fallback;
      return list[0]?.id ?? "";
    });
  }, [conf]);

  const sel = teams.find((t) => t.id === selId) ?? teams[0];
  const players = useMemo(
    () => sortPlayers(sel?.players ?? [], sortBy),
    [sel, sortBy],
  );
  const rotation = useMemo(
    () => coreRotation(sel?.players ?? []),
    [sel],
  );
  const playerRole = (id) => {
    if (rotation.starterIds.has(id)) return "starter";
    if (rotation.benchIds.has(id)) return "bench";
    return null;
  };
  const totalPlayers = teams.reduce((n, t) => n + (t.players?.length ?? 0), 0);

  return (
    <div className="roster-page">
      <div className="roster-toolbar">
        <div className="roster-toolbar-title">
          <div className="roster-toolbar-heading">B.PREMIER {CONFERENCES[conf].label}</div>
          <div className="roster-toolbar-meta">{ROSTERS.season} · 갱신 {ROSTERS.updated} · {totalPlayers}명</div>
        </div>
        <div className="roster-conf-switch">
          {Object.entries(CONFERENCES).map(([key, { label }]) => (
            <button key={key} type="button" onClick={() => setConf(key)} className={conf === key ? "active" : ""}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="roster-team-tabs">
        <div className="roster-team-tabs-inner">
          {teams.map((t, i) => {
            const active = selId === t.id;
            return (
              <button key={t.id} type="button" onClick={() => setSelId(t.id)} className={active ? "active" : ""} style={{
                borderBottomColor: active ? t.accent : "transparent",
                background: active ? `${t.primary}44` : "transparent",
                color: active ? t.accent : "#64748B",
              }}>
                <img src={t.logo_url} alt="" style={{ width: 18, height: 18, objectFit: "contain", opacity: active ? 1 : 0.55 }} />
                <span>{String(i + 1).padStart(2, "0")} {t.name_korean}</span>
                <span className="count">({t.players.length})</span>
              </button>
            );
          })}
        </div>
      </div>

      {teams.length === 0 ? (
        <div style={{ textAlign: "center", padding: "64px 22px", color: "#64748B" }}>
          {CONFERENCES[conf].label} 데이터 없음.<br />
          <code style={{ fontSize: "12px" }}>python crawl_bleague_rosters.py --{conf}</code> 실행 후 새로고침하세요.
        </div>
      ) : (
        <>
          <div className="roster-team-header" style={{ borderBottomColor: `${sel.primary}44`, background: `linear-gradient(90deg, ${sel.primary}33, transparent)` }}>
            <img src={sel.logo_url} alt="" style={{ width: 44, height: 44, objectFit: "contain" }} />
            <div>
              <div style={{ fontSize: "20px", fontWeight: 700 }}>{sel.name_korean}</div>
              <div style={{ fontSize: "12px", color: "#64748B" }}>
                2025-26 · {SORTS[sortBy].label} 순 ·
                <span style={{ color: sel.accent }}> 주전 {rotation.starterIds.size}</span>
                {" · "}
                <span style={{ color: sel.primary }}>벤치 {rotation.benchIds.size}</span>
              </div>
            </div>
            <div className="roster-sort">
              <span>정렬</span>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                {Object.entries(SORTS).map(([key, { label }]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
              <span className="count">{players.length}명</span>
            </div>
          </div>

          <div style={{ padding: "20px 22px" }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(155px, 1fr))", gap: "12px" }}>
              {players.map((pl, i) => (
                <PlayerCard key={pl.player_id} player={pl} team={sel} idx={i} sortBy={sortBy} role={playerRole(pl.player_id)} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
