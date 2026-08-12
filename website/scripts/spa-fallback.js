import { copyFileSync, mkdirSync, existsSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const dist = join(root, 'dist')
const index = join(dist, 'index.html')
if (!existsSync(index)) {
  console.error('spa-fallback: dist/index.html missing')
  process.exit(1)
}
const routes = ['marketplace']
for (const route of routes) {
  const dir = join(dist, route)
  mkdirSync(dir, { recursive: true })
  copyFileSync(index, join(dir, 'index.html'))
  console.log(`spa-fallback: wrote ${route}/index.html`)
}
