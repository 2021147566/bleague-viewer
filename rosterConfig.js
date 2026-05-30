import ROSTERS from "./bleague-rosters.json";

export const CONFERENCES = {
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

export function teamList(conf) {
  const order = CONFERENCES[conf].order;
  return order
    .filter((id) => ROSTERS.teams[id])
    .map((id) => ({ id, conference: conf, ...ROSTERS.teams[id] }));
}

export { ROSTERS };
