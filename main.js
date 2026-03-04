/**
 * The KAKASHI Recon V 1.1 — Electron Main Process
 * Handles window creation, Python spawning, IPC, and file I/O.
 */

const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const path  = require('path');
const fs    = require('fs');
const os    = require('os');

let mainWindow  = null;
let scanProcess = null;

// ── Window ────────────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width:           1380,
    height:          860,
    minWidth:        1100,
    minHeight:       680,
    backgroundColor: '#0d1117',
    titleBarStyle:   'default',
    frame:           true,
    show:            false,
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
    },
  });

  mainWindow.loadFile('index.html');
  mainWindow.setMenuBarVisibility(false);

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    if (scanProcess) { scanProcess.kill(); scanProcess = null; }
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (scanProcess) { scanProcess.kill(); scanProcess = null; }
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

// ── IPC: Start Scan ───────────────────────────────────────────────────────────
ipcMain.handle('start-scan', (event, { domain, modules, output }) => {
  if (scanProcess) {
    try { scanProcess.kill(); } catch (_) {}
    scanProcess = null;
  }

  const scriptPath = path.join(__dirname, 'kakashi_recon.py');

  if (!fs.existsSync(scriptPath)) {
    return { success: false, error: 'kakashi_recon.py not found in tool directory.' };
  }

  // Try 'python' first (Windows default), fall back handled via error event
  const args = [scriptPath, domain, '-m', modules, '-o', output];

  try {
    scanProcess = spawn('python', args, {
      cwd: __dirname,
      env: { ...process.env },
    });
  } catch (e) {
    // Fallback to python3
    try {
      scanProcess = spawn('python3', args, { cwd: __dirname, env: { ...process.env } });
    } catch (e2) {
      return { success: false, error: 'Python not found. Make sure Python is installed and in PATH.' };
    }
  }

  scanProcess.stdout.on('data', (data) => {
    if (mainWindow) {
      mainWindow.webContents.send('scan-output', { type: 'stdout', data: data.toString() });
    }
  });

  scanProcess.stderr.on('data', (data) => {
    if (mainWindow) {
      mainWindow.webContents.send('scan-output', { type: 'stderr', data: data.toString() });
    }
  });

  scanProcess.on('close', (code) => {
    if (mainWindow) mainWindow.webContents.send('scan-complete', { code });
    scanProcess = null;
  });

  scanProcess.on('error', (err) => {
    if (mainWindow) {
      mainWindow.webContents.send('scan-output', {
        type: 'error',
        data: `\nProcess error: ${err.message}\nMake sure Python is installed and in your PATH.\n`,
      });
      mainWindow.webContents.send('scan-complete', { code: -1 });
    }
    scanProcess = null;
  });

  return { success: true };
});

// ── IPC: Stop Scan ────────────────────────────────────────────────────────────
ipcMain.handle('stop-scan', () => {
  if (scanProcess) {
    try { scanProcess.kill(); } catch (_) {}
    scanProcess = null;
    return { success: true };
  }
  return { success: false };
});

// ── IPC: Read JSON report ─────────────────────────────────────────────────────
ipcMain.handle('read-report', (event, { domain, output }) => {
  const reportPath = path.join(__dirname, output, `${domain}_report.json`);
  try {
    if (fs.existsSync(reportPath)) {
      const raw  = fs.readFileSync(reportPath, 'utf-8');
      const data = JSON.parse(raw);
      return { success: true, data };
    }
    return { success: false, error: 'Report file not found.' };
  } catch (e) {
    return { success: false, error: e.message };
  }
});

// ── IPC: Open output directory in Explorer ────────────────────────────────────
ipcMain.handle('open-output-dir', (event, { output }) => {
  const dirPath = path.join(__dirname, output);
  if (!fs.existsSync(dirPath)) fs.mkdirSync(dirPath, { recursive: true });
  shell.openPath(dirPath);
  return { success: true };
});

// ── IPC: Browse for directory ─────────────────────────────────────────────────
ipcMain.handle('select-dir', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
    title: 'Select Output Directory',
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return { path: result.filePaths[0] };
  }
  return { path: null };
});

// ── IPC: Save text file (HTML / CSV / JSON) ───────────────────────────────────
ipcMain.handle('save-file', async (event, { content, defaultName, filters }) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    title:       'Save Report',
    defaultPath: defaultName || 'report',
    filters:     filters || [{ name: 'All Files', extensions: ['*'] }],
  });
  if (!result.canceled && result.filePath) {
    try {
      fs.writeFileSync(result.filePath, content, 'utf-8');
      return { success: true, filePath: result.filePath };
    } catch (e) {
      return { success: false, error: e.message };
    }
  }
  return { success: false, error: 'cancelled' };
});

// ── IPC: Generate PDF via hidden BrowserWindow ────────────────────────────────
ipcMain.handle('generate-pdf', async (event, { htmlContent, defaultName }) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    title:       'Save PDF Report',
    defaultPath: defaultName || 'report.pdf',
    filters:     [{ name: 'PDF Files', extensions: ['pdf'] }],
  });
  if (!result.canceled && result.filePath) {
    const tempFile = path.join(os.tmpdir(), `kakashi_recon_${Date.now()}.html`);
    try {
      fs.writeFileSync(tempFile, htmlContent, 'utf-8');
      const pdfWin = new BrowserWindow({
        show: false,
        webPreferences: { nodeIntegration: false, contextIsolation: true },
      });
      await pdfWin.loadFile(tempFile);
      const pdfBuffer = await pdfWin.webContents.printToPDF({
        printBackground: true,
        pageSize:        'A4',
        margins:         { marginType: 'custom', top: 0.5, bottom: 0.5, left: 0.5, right: 0.5 },
      });
      pdfWin.destroy();
      try { fs.unlinkSync(tempFile); } catch (_) {}
      fs.writeFileSync(result.filePath, pdfBuffer);
      return { success: true, filePath: result.filePath };
    } catch (e) {
      try { fs.unlinkSync(tempFile); } catch (_) {}
      return { success: false, error: e.message };
    }
  }
  return { success: false, error: 'cancelled' };
});
