/** @jest-environment node */
import { createServer } from "node:http";
import { AddressInfo } from "node:net";
import { NextRequest } from "next/server";
import { GET, POST } from "./route";

test("missing backend fails closed without revealing configuration", async () => {
  const original = process.env.BACKEND_URL;
  delete process.env.BACKEND_URL;
  try {
    const response = await GET(new NextRequest("http://frontend/api/notes"));
    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ error: "Backend unavailable" });
  } finally {
    if (original === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = original;
  }
});

test("server proxy forwards notes path and JSON, preserving validation status", async () => {
  const received: { method: string; path: string; body: string }[] = [];
  const server = createServer(async (request, response) => {
    let body = "";
    for await (const chunk of request) body += chunk;
    received.push({ method: request.method!, path: request.url!, body });
    response.writeHead(request.method === "POST" ? 400 : 200, { "Content-Type": "application/json" });
    response.end(request.method === "POST" ? '{"error":"length"}' : '[]');
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  const original = process.env.BACKEND_URL;
  process.env.BACKEND_URL = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  try {
    const listed = await GET(new NextRequest("http://frontend/api/notes"));
    expect(await listed.json()).toEqual([]);
    expect(listed.headers.get("Cache-Control")).toBe("no-store");
    const posted = await POST(new NextRequest("http://frontend/api/notes", { method: "POST", body: '{"text":""}' }));
    expect(posted.status).toBe(400);
    expect(received).toEqual([
      { method: "GET", path: "/notes", body: "" },
      { method: "POST", path: "/notes", body: '{"text":""}' },
    ]);
  } finally {
    if (original === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = original;
    await new Promise<void>((resolve, reject) => server.close(e => e ? reject(e) : resolve()));
  }
});
