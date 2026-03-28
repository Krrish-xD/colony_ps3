import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0E14",
        cyber: {
          cyan: "#00E5FF",
          red: "#FF3B5C",
          pink: "#FF6B8B",
          yellow: "#FFD166",
          dark: "#151A23",
          darker: "#0B0E14",
          light: "#E2E8F0",
          dim: "#4A5568",
          gray: "#2A3143"
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', "monospace"],
        sans: ['"Inter"', "sans-serif"]
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic":
          "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
      },
    },
  },
  plugins: [],
};
export default config;