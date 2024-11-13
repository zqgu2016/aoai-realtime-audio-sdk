import {defineConfig} from 'vite'
import mkcert from 'vite-plugin-mkcert'

// https://vitejs.dev/config/
export default defineConfig({
  server: {
    https: true,
    host: '0.0.0.0',
		port: 5174,
  }, // Not needed for Vite 5+ (simply omit this option)
  plugins: [mkcert()]
})