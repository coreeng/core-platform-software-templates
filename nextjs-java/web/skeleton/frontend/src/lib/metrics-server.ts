import { createServer } from "node:http";
import { collectDefaultMetrics, register } from "prom-client";
collectDefaultMetrics();
createServer(async (request, response) => {
  if (request.url !== "/metrics") { response.writeHead(404).end(); return; }
  response.setHeader("Content-Type", register.contentType);
  response.end(await register.metrics());
}).listen(Number(process.env.METRICS_PORT || 8081), "0.0.0.0");
