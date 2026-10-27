module.exports = {
  content: ['./src/templates/**/*.html', './src/static/js/**/*.js',
    './src/seoapp/**/*.py', './src/conversation/**/*.py', './src/reignitehome/**/*.py'],
  darkMode: 'class',
  theme: { extend: {
    colors: {
      brand: {bg: '#12141A', surface: '#16181F', primary: '#FF2D6D', secondary: '#D4AF37',
        tertiary: '#FF2D6D', text: '#F4F2EE', muted: '#8F9BB3', outline: '#3A3F4A',
        blush: '#1B1E25', 'outline-variant': '#2E323B', 'surface-dim': '#101218', 'surface-container': '#16181F'},
      dbrand: {bg: '#12141A', surface: '#16181F', primary: '#FF2D6D', secondary: '#D4AF37',
        tertiary: '#FF2D6D', text: '#F4F2EE', muted: '#8F9BB3', outline: '#3A3F4A',
        'outline-variant': '#2E323B', 'surface-container': '#16181F', 'surface-high': '#1B1E25', 'surface-low': '#101218'},
    },
    fontFamily: {heading: ['"Playfair Display"', 'serif'], body: ['Inter', 'system-ui', 'sans-serif']},
    borderRadius: {xl: '12px', '2xl': '12px'},
  }},
  plugins: [],
};
