// Tailwind v3 build for the Haze Monitor. Colors come from CSS variables (same tokens as Sea basic),
// so light and dark themes switch without dark: variants.
//   npx tailwindcss@3.4.17 -c haze/tailwind.config.js -i haze/src.css -o haze/haze.css --minify
module.exports = {
  content: ['./haze/index.html', './haze/app.js'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)', panel: 'var(--panel)', fg: 'var(--fg)', muted: 'var(--muted)', line: 'var(--line)',
        frame: 'var(--frame)', accent: 'var(--accent)', 'on-accent': 'var(--on-accent)', 'accent-soft': 'var(--accent-soft)',
        'accent-line': 'var(--accent-line)', rust: 'var(--rust)', 'mustard-soft': 'var(--mustard-soft)', 'mustard-line': 'var(--mustard-line)',
      },
      fontFamily: { sans: ['"Noto Sans JP"', '"Hiragino Sans"', '"Yu Gothic"', 'system-ui', 'sans-serif'] },
      borderRadius: { card: '6px' },
    },
  },
};
