/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        headline: ['"Euro Technic"', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        kingcap: {
          gold: '#D4AF37',
          navy: '#1a365d',
          dark: '#0f172a',
        },
        // HIG-flavored semantic surfaces (dark appearance).
        // Use these instead of raw gray-900/800 for new work; existing
        // gray classes still work for backward compatibility.
        surface: {
          base: '#000000',
          elevated: '#1c1c1e',
          raised: '#2c2c2e',
          floating: '#3a3a3c',
        },
      },
      backgroundColor: {
        // System fills (HIG): translucent grays that adapt to underlying surface
        'fill-primary': 'rgba(120, 120, 128, 0.36)',
        'fill-secondary': 'rgba(120, 120, 128, 0.32)',
        'fill-tertiary': 'rgba(118, 118, 128, 0.24)',
        'fill-quaternary': 'rgba(116, 116, 128, 0.18)',
      },
      borderColor: {
        // Hairline separator at HIG-spec opacity
        separator: 'rgba(84, 84, 88, 0.65)',
        'separator-opaque': '#38383a',
      },
      borderRadius: {
        // HIG corner-radius scale
        'hig-sm': '6px',
        'hig-md': '10px',
        'hig-lg': '14px',
        'hig-xl': '20px',
      },
      boxShadow: {
        // Layered HIG-style shadows with color tint instead of flat black
        'hig-1': '0 1px 2px rgba(0,0,0,0.30), 0 1px 1px rgba(0,0,0,0.20)',
        'hig-2': '0 4px 12px rgba(0,0,0,0.35), 0 1px 3px rgba(0,0,0,0.25)',
        'hig-3': '0 12px 32px rgba(0,0,0,0.45), 0 4px 12px rgba(0,0,0,0.30)',
        'hig-inset': 'inset 0 1px 0 rgba(255,255,255,0.06)',
      },
      backdropBlur: {
        'material-thin': '20px',
        'material-regular': '40px',
        'material-thick': '60px',
      },
      transitionTimingFunction: {
        // HIG-ish spring easing for press states
        'hig': 'cubic-bezier(0.32, 0.72, 0, 1)',
      },
    },
  },
  plugins: [],
}
