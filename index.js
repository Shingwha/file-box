const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3000;
const UPLOAD_DIR = process.env.RAILWAY_VOLUME_MOUNT_PATH
  || path.resolve(process.env.UPLOAD_DIR || './data');
const PASSWORD = process.env.PASSWORD || '';
const MAX_SIZE = 500 * 1024 * 1024; // 500 MB

// Ensure upload dir exists
fs.mkdirSync(UPLOAD_DIR, { recursive: true });

// ---- Auth ----
function requireAuth(req, res, next) {
  if (!PASSWORD) return next();
  const token = req.query.token || req.headers['x-auth-token'];
  if (token) {
    const expected = crypto.createHash('sha256').update(PASSWORD).digest('hex');
    if (token === expected) return next();
  }
  return res.status(401).json({ error: 'unauthorized', needAuth: true });
}

// GET /api/status — public, tells frontend if password is needed
app.get('/api/status', (req, res) => {
  res.json({ auth: !!PASSWORD });
});

// GET /api/storage — storage usage (calculates from actual files)
app.get('/api/storage', requireAuth, (req, res) => {
  try {
    // Guess quota from env or use a sensible default
    let quotaBytes = parseInt(process.env.STORAGE_LIMIT) || 0;
    if (!quotaBytes) {
      // Railway Volume Free = 0.5 GB, Hobby = 5 GB
      quotaBytes = process.env.RAILWAY_VOLUME_MOUNT_PATH
        ? 0.5 * 1073741824  // assume Free plan
        : 500 * 1048576;    // no volume → 500 MB ephemeral
    }
    const toHuman = b => b > 1073741824
      ? (b / 1073741824).toFixed(1) + ' GB'
      : (b / 1048576).toFixed(1) + ' MB';
    let fileCount = 0, usedBytes = 0;
    try {
      const entries = fs.readdirSync(UPLOAD_DIR);
      entries.forEach(f => {
        const fp = path.join(UPLOAD_DIR, f);
        const st = fs.statSync(fp);
        if (st.isFile()) { fileCount++; usedBytes += st.size; }
      });
    } catch(e) {}
    const freeBytes = Math.max(0, quotaBytes - usedBytes);
    const pct = quotaBytes > 0 ? ((usedBytes / quotaBytes) * 100).toFixed(1) + '%' : '?';
    res.json({
      total: toHuman(quotaBytes),
      used: toHuman(usedBytes),
      free: toHuman(freeBytes),
      usagePercent: pct,
      files: fileCount
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// POST /api/auth — verify password, return token
app.post('/api/auth', express.json(), (req, res) => {
  if (!PASSWORD) return res.json({ ok: true, token: '' });
  if (req.body.password === PASSWORD) {
    const token = crypto.createHash('sha256').update(PASSWORD).digest('hex');
    return res.json({ ok: true, token });
  }
  return res.status(403).json({ ok: false, error: 'wrong password' });
});

// ---- Multer ----
const storage = multer.diskStorage({
  destination: UPLOAD_DIR,
  filename: (req, file, cb) => {
    // Fix encoding: multer decodes as latin-1, we need utf-8 for Chinese
    let name = file.originalname;
    try {
      const buf = Buffer.from(file.originalname, 'latin1');
      name = buf.toString('utf8');
    } catch(e) {}
    cb(null, name.replace(/[<>:"/\\|?*]/g, '_').trim());
  }
});
const upload = multer({ storage, limits: { fileSize: MAX_SIZE } });

// GET /api/files — list all files
app.get('/api/files', requireAuth, (req, res) => {
  try {
    const files = fs.readdirSync(UPLOAD_DIR)
      .filter(f => fs.statSync(path.join(UPLOAD_DIR, f)).isFile())
      .map(f => {
        const stat = fs.statSync(path.join(UPLOAD_DIR, f));
        const size = stat.size > 1048576
          ? (stat.size / 1048576).toFixed(1) + ' MB'
          : (stat.size / 1024).toFixed(1) + ' KB';
        return { name: f, size, sizeBytes: stat.size, mtime: stat.mtime.toISOString() };
      })
      .sort((a, b) => b.mtime.localeCompare(a.mtime));
    res.json({ files });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// POST /api/upload — upload files
app.post('/api/upload', requireAuth, upload.array('file', 50), (req, res) => {
  if (!req.files || req.files.length === 0) {
    return res.status(400).json({ error: 'No files uploaded' });
  }
  const uploaded = req.files.map(f => ({
    filename: f.filename,
    size: f.size > 1048576 ? (f.size / 1048576).toFixed(1) + ' MB' : (f.size / 1024).toFixed(1) + ' KB'
  }));
  res.json({ success: true, files: uploaded });
});

// GET /api/files/:name — download a file
app.get('/api/files/:name', requireAuth, (req, res) => {
  const name = path.basename(req.params.name);
  const fp = path.join(UPLOAD_DIR, name);
  if (!fs.existsSync(fp)) return res.status(404).json({ error: 'File not found' });
  res.setHeader('Content-Disposition',
    `attachment; filename="${name.replace(/[^\x20-\x7E]/g, '_')}"; filename*=UTF-8''${encodeURIComponent(name)}`);
  res.sendFile(fp);
});

// DELETE /api/files/:name — delete a file
app.delete('/api/files/:name', requireAuth, (req, res) => {
  const name = path.basename(req.params.name);
  const fp = path.join(UPLOAD_DIR, name);
  if (!fs.existsSync(fp)) return res.status(404).json({ error: 'File not found' });
  try {
    fs.unlinkSync(fp);
    res.json({ success: true });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Serve frontend
app.use(express.static(path.join(__dirname, 'public')));
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[file-box] v1.0.1 running on port ${PORT}`);
  console.log(`[file-box] storage: ${UPLOAD_DIR}`);
  console.log(`[file-box] auth: ${PASSWORD ? 'password enabled' : 'public (no password)'}`);
});
