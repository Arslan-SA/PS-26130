import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        gov: {
          blue: "#0B3C5D",
          dark: "#1D2731",
          gold: "#D9B310",
          sky: "#328CC1",
          light: "#F9FBFC",
          card: "#FFFFFF",
          border: "#E2E8F0"
        }
      },
    },
  },
  plugins: [],
};
export default config;
