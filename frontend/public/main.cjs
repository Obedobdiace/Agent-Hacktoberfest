const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');

let mainWindow;

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  // Fenêtre en plein écran-ish mais déplaçable et redimensionnable
  const winWidth  = Math.min(900, width);
  const winHeight = Math.min(700, height - 60);
  const startX    = Math.round((width  - winWidth)  / 2);
  const startY    = Math.round((height - winHeight) / 2);

  mainWindow = new BrowserWindow({
    width:       winWidth,
    height:      winHeight,
    x:           startX,
    y:           startY,
    frame:       false,       // Pas de barre de titre native (on gère le drag dans le CSS)
    transparent: true,        // Fond transparent pour l'effet frosted glass
    alwaysOnTop: false,       // ← DÉSACTIVÉ : la fenêtre ne bloque plus les autres apps
    skipTaskbar: false,       // ← Visible dans la barre des tâches
    resizable:   true,        // Redimensionnable
    movable:     true,        // Déplaçable
    minWidth:    600,
    minHeight:   500,
    webPreferences: {
      nodeIntegration:  true,
      contextIsolation: false
    }
  });

  const startUrl = isDev
    ? 'http://localhost:5173'
    : `file://${path.join(__dirname, '../dist/index.html')}`;

  mainWindow.loadURL(startUrl);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Drag depuis le frontend via IPC
ipcMain.on('start-drag', () => {
  // handled natively via -webkit-app-region: drag in CSS
});

// Toggle alwaysOnTop depuis le frontend (bouton épingler)
ipcMain.on('toggle-always-on-top', () => {
  if (!mainWindow) return;
  const current = mainWindow.isAlwaysOnTop();
  mainWindow.setAlwaysOnTop(!current);
  mainWindow.webContents.send('always-on-top-changed', !current);
});

// Minimiser / fermer depuis le frontend
ipcMain.on('minimize-window', () => { if (mainWindow) mainWindow.minimize(); });
ipcMain.on('close-window',    () => { if (mainWindow) mainWindow.close(); });
