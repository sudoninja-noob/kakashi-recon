/**
 * The KAKASHI Recon V 1.1 — Preload / IPC Bridge
 * Safely exposes Electron APIs to the renderer via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // Scan control
  startScan:    (opts)  => ipcRenderer.invoke('start-scan', opts),
  stopScan:     ()      => ipcRenderer.invoke('stop-scan'),

  // Results
  readReport:   (opts)  => ipcRenderer.invoke('read-report', opts),

  // File system
  openOutputDir:(opts)  => ipcRenderer.invoke('open-output-dir', opts),
  selectDir:    ()      => ipcRenderer.invoke('select-dir'),

  // Report export
  saveFile:    (opts)  => ipcRenderer.invoke('save-file', opts),
  generatePdf: (opts)  => ipcRenderer.invoke('generate-pdf', opts),

  // Event listeners (renderer subscribes to main-process events)
  onScanOutput: (cb) =>
    ipcRenderer.on('scan-output',  (_, data) => cb(data)),

  onScanComplete: (cb) =>
    ipcRenderer.on('scan-complete', (_, data) => cb(data)),

  // Cleanup
  removeListeners: () => {
    ipcRenderer.removeAllListeners('scan-output');
    ipcRenderer.removeAllListeners('scan-complete');
  },
});
