export const teamColors = {
  ARS: "#EF0107",
  AVL: "#95BFE5",
  BOU: "#DA291C",
  BRE: "#E30613",
  BHA: "#0057B8",
  CHE: "#034694",
  CRY: "#1B458F",
  EVE: "#003399",
  FUL: "#FFFFFF",
  LIV: "#C8102E",
  MCI: "#6CABDD",
  MUN: "#DA291C",
  NEW: "#241F20",
  NFO: "#DD0000",
  TOT: "#132257",
  WHU: "#7A263A",
  WOL: "#FDB913",
  IPW: "#0033A0",
  LEI: "#003090",
  SOU: "#D71920",
}

export const getTeamColor = (team) => teamColors[team] || "#888888"
