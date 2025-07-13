/* eslint-disable @typescript-eslint/consistent-type-imports */
const BACKEND_PORT   = import.meta.env.VITE_BACKEND_PORT || "8000";
const SECURE         = location.protocol === "https:";
const SCHEME         = SECURE ? "wss" : "ws";

/**
 * Определяем хост backend'а.
 *
 *  •  В Codespaces front-host = 5173-<hash>.app.github.dev
 *     backend-host должен быть 8000-<hash>.app.github.dev  (без :PORT!)
 *
 *  •  Локально  front-host = localhost:5173
 *     backend-host = localhost:8000
 *
 *  •  В докер-проде  front-host = hostname,  BACKEND_HOST=backend
 */
function backendHost(): string {
  // GH-Codespaces: …-5173.app.github.dev   →   …-8000.app.github.dev
  const m = location.hostname.match(/-(\d+)\.app\.github\.dev$/);
  if (m) {
    return location.hostname.replace(/-\d+\.app\.github\.dev$/, "-8000.app.github.dev");
  }
  // остальное без изменений
  const env = import.meta.env.VITE_BACKEND_HOST;
  if (env && env !== "backend") return env;
  return location.hostname;
}

/**
 * Строим URL:
 *   Codespaces → wss://8000-....app.github.dev/ws
 *   Local      → ws://localhost:8000/ws
 *   Docker prod→ ws://backend:8000/ws   (фронт и бэк в одной сети)
 */
function buildWsUrl(): string {
  const host = backendHost();
  // в GH-preview port уже «зашит» в hostname, доппорт не нужен
  const needPort = !host.endsWith(".app.github.dev");
  return needPort
    ? `${SCHEME}://${host}:${BACKEND_PORT}/ws`
    : `${SCHEME}://${host}/ws`;
}

export const WS_URL = buildWsUrl();
console.log("%cWS_URL", "color:orange", WS_URL);
