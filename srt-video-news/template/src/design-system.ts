export const designTokens = {
  background: {
    host: "#F5F2EB",
    paper: "#FFFFFF",
    dark: "#14161c",
  },
  text: {
    primary: "#1a1a1a",
    secondary: "#555",
    muted: "#888",
    onDark: "#eee",
  },
  accent: {
    primary: "#C41E24",
    secondary: "#8B0000",
    blue: "#2E5C8A",
    gold: "#B8860B",
  },
  surface: {
    card: "#FFFFFF",
    line: "#d4d0c8",
  },
} as const;

export const hostDecor = {
  gridSize: "0px 0px",
  gridSizePx: 0,
  gridOpacity: 0,
  gridScrollSpeed: 0,
  sparkles: [] as const,
} as const;
