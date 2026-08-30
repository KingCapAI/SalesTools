/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Nunito', 'system-ui', 'sans-serif'],
      },
      colors: {
        ink: '#221833',
        cream: '#FFF8F0',
        pop: {
          coral: '#FF6B6B',
          tangerine: '#FF9F43',
          sunshine: '#FFD93D',
          mint: '#6BCB77',
          sky: '#4D96FF',
          grape: '#9B5DE5',
        },
      },
      borderRadius: {
        blob: '1.75rem',
      },
      boxShadow: {
        pop: '0 6px 0 rgba(34, 24, 51, 0.9)',
        poplite: '0 3px 0 rgba(34, 24, 51, 0.9)',
      },
    },
  },
  plugins: [],
}
