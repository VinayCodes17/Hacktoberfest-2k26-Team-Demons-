import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
async function proxy(request: NextRequest, context: {params: Promise<{path: string[]}>}) {
  const {path} = await context.params;
  const resource = path.join("/");
  const allowed = request.method === "POST"
    ? /^(datasets\/profile|jobs)$/.test(resource)
    : /^(readiness|jobs\/[a-zA-Z0-9-]+(\/(progress|predictions|export.xlsx))?)$/.test(resource);
  if (!allowed) return Response.json({message: "Unknown API route."}, {status: 404});
  const length = Number(request.headers.get("content-length") || 0);
  if (length > 51 * 1024 * 1024) return Response.json({message: "Workbook exceeds 50 MiB."}, {status: 413});
  const base = process.env.HISABHPARAKH_API_URL ?? "http://127.0.0.1:8000";
  try {
    const headers = new Headers();
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);
    const options: RequestInit & {duplex?: "half"} = {
      method: request.method, headers, cache: "no-store", signal: AbortSignal.timeout(120000),
    };
    if (request.method === "POST") { options.body = request.body; options.duplex = "half"; }
    const upstream = await fetch(`${base}/api/v1/${resource}`, options);
    const responseHeaders = new Headers({"Cache-Control": "no-store"});
    for (const name of ["content-type", "content-disposition"]) {
      const value = upstream.headers.get(name); if (value) responseHeaders.set(name, value);
    }
    return new Response(upstream.body, {status: upstream.status, headers: responseHeaders});
  } catch {
    return Response.json({message: "The local service did not respond. Your saved job is safe; retry when the service is available."}, {status: 502});
  }
}
export {proxy as GET, proxy as POST};
