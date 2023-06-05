// example usage: node ./env_installer/construct.js linux x86_64

/*import { spawn } from 'child_process'
import * as url from 'url'
import path from 'path'

const __dirname = url.fileURLToPath(new URL('.', import.meta.url))

const platform = process.env.TAURI_PLATFORM || process.argv[2]
const arch = process.env.TAURI_ARCH || process.argv[3]

let platformName = ''
switch (platform) {
  case 'macos':
    platformName = 'osx'
    break
  case 'windows':
    platformName = 'win'
    break
  default:
    platformName = platform
}

let platformArch = ''
switch (arch) {
  case 'x86':
    platformArch = '32'
    break
  case 'x86_64':
    platformArch = '64'
    break
  case 'aarch64':
    platformArch = 'arm64'
    break
  default:
    platformArch = arch
}

console.log(`Building installer for ${platformName}-${platformArch}`)

spawn('constructor', [__dirname, `--platform=${platformName}-${platformArch}`, '--output-dir', path.resolve(__dirname, '../src-tauri')], { stdio: 'inherit' })
*/