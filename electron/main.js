const { app, BrowserWindow, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')
const net = require('net')

let mainWindow = null
let backendProcess = null

function getAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
    server.on('error', reject)
  })
}

function getBackendPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend.exe')
  }
  return path.join(__dirname, '..', 'dist-backend', 'backend.exe')
}

function getResourcesPath() {
  if (app.isPackaged) {
    return process.resourcesPath
  }
  return path.join(__dirname, '..')
}

function waitForBackend(url, maxRetries = 60) {
  return new Promise((resolve, reject) => {
    let retries = 0
    const check = () => {
      http.get(url + '/api/projects', (res) => {
        resolve()
      }).on('error', () => {
        retries++
        if (retries >= maxRetries) {
          reject(new Error('Backend failed to start'))
        } else {
          setTimeout(check, 500)
        }
      })
    }
    check()
  })
}

async function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    title: '织镜',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  })

  const url = `http://127.0.0.1:${port}`
  mainWindow.loadURL(url)

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(async () => {
  try {
    const port = await getAvailablePort()
    const backendPath = getBackendPath()

    const appDataEnv = process.env.APPDATA || path.join(app.getPath('home'), 'AppData', 'Roaming')
    const dataDir = path.join(appDataEnv, '织镜')
    const resourcesPath = getResourcesPath()

    backendProcess = spawn(backendPath, [], {
      env: {
        ...process.env,
        STORYFORGE_PORT: String(port),
        STORYFORGE_DATA_DIR: dataDir,
        STORYFORGE_RESOURCES_DIR: resourcesPath,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    backendProcess.stdout.on('data', (data) => {
      console.log(`[backend] ${data}`)
    })
    backendProcess.stderr.on('data', (data) => {
      console.error(`[backend] ${data}`)
    })
    backendProcess.on('error', (err) => {
      dialog.showErrorBox('启动失败', `无法启动后端服务: ${err.message}`)
      app.quit()
    })

    await waitForBackend(`http://127.0.0.1:${port}`)
    await createWindow(port)
  } catch (err) {
    dialog.showErrorBox('启动失败', err.message)
    app.quit()
  }
})

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
  app.quit()
})

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
})
