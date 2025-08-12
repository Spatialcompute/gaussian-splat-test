import express from 'express';
import compression from 'compression';
import morgan from 'morgan';
import { ThrottleGroup } from 'stream-throttle';
import path from 'path';
import fs from 'fs';

const app = express();
const PORT = process.env.PORT || 8080;
const ROOT = path.resolve(path.join(process.cwd(), '..', 'demo'));

app.use(morgan('dev'));
app.use(compression());

// Throttle large .dat streaming so the viewer behaves like remote hosting
const MBPS = Number(process.env.THROTTLE_MBPS || '25'); // ~close to remote default
const tg = new ThrottleGroup({ rate: Math.max(1, Math.floor(MBPS * 1024 * 1024 / 8)) });

app.get('/data/:file', (req, res, next) => {
  const file = req.params.file;
  const full = path.join(ROOT, 'data', file);
  if (!fs.existsSync(full)) return res.status(404).end();
  res.setHeader('Content-Type', 'application/octet-stream');
  const rs = fs.createReadStream(full);
  const throttled = tg.throttle();
  rs.on('open', () => rs.pipe(throttled).pipe(res));
  rs.on('error', next);
});

// Serve demo static files
app.use(express.static(ROOT));

app.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
  console.log(`Serving ${ROOT} with throttle ~${MBPS} Mbps for /data/*.dat`);
});
