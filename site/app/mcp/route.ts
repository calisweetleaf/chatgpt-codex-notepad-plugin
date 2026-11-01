import { env } from "cloudflare:workers";
import server, { type Environment } from "../../workspace-generated/hosted/index";
export const dynamic = "force-dynamic";
export async function POST(request: Request) { return server.fetch(request, env as unknown as Environment); }
export async function GET(request: Request) { return server.fetch(request, env as unknown as Environment); }
