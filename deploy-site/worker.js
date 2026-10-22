// Runs only for /media/* (see run_worker_first in wrangler.jsonc); every other path is served
// straight from static assets with the headers in site-build/_headers.
// Why: static assets answer 200 with the whole file, and Safari on iPhone will not play an MP4
// unless Range requests get 206. This answers byte ranges and sets a cache header for media.
// The explainer video is a few tens of MB at most, so slicing in memory is fine.
export default {
  async fetch(request, env) {
    const range = request.headers.get("Range");
    const plain = new Headers(request.headers);
    plain.delete("Range");
    const res = await env.ASSETS.fetch(new Request(request.url, { method: "GET", headers: plain }));
    if (res.status !== 200) return res;

    const headers = new Headers(res.headers);
    headers.set("Cache-Control", "public, max-age=86400, stale-while-revalidate=604800");
    headers.set("Accept-Ranges", "bytes");

    const m = range && /^bytes=(\d*)-(\d*)$/.exec(range.trim());
    if (!m || (m[1] === "" && m[2] === "")) {
      return new Response(request.method === "HEAD" ? null : res.body, { status: 200, headers });
    }
    const buf = await res.arrayBuffer();
    const size = buf.byteLength;
    let start, end;
    if (m[1] === "") { start = Math.max(0, size - Number(m[2])); end = size - 1; }
    else { start = Number(m[1]); end = m[2] === "" ? size - 1 : Math.min(Number(m[2]), size - 1); }
    if (start >= size || start > end) {
      headers.set("Content-Range", `bytes */${size}`);
      headers.delete("Content-Length");
      return new Response(null, { status: 416, headers });
    }
    headers.set("Content-Range", `bytes ${start}-${end}/${size}`);
    headers.set("Content-Length", String(end - start + 1));
    return new Response(request.method === "HEAD" ? null : buf.slice(start, end + 1), { status: 206, headers });
  },
};
