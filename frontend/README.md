# Assistly frontend

React, Vite, React Router data APIs, and Redux Toolkit interface for the FastAPI support service.

## Run locally

1. Start the backend at `http://localhost:8000` (setup instructions are in [`../backend/README.md`](../backend/README.md)).
2. In this directory, run `npm install` and `npm run dev`.
3. Vite is pinned to `http://localhost:5173` so it matches the backend's default CORS allowlist. To use another frontend origin, add that exact origin (scheme and port included, with no trailing slash) to `ALLOWED_ORIGINS` in the backend environment. To use another API URL, copy `.env.example` to `.env.local` and set `VITE_API_URL`.

Use `npm run build` to create the production bundle, or `npm run preview` to serve it locally. For deployment, set `VITE_API_URL` to the HTTPS API origin at build time, add the exact HTTPS frontend origin to the backend `ALLOWED_ORIGINS`, and configure the deployment host to serve `index.html` for frontend routes. Do not deploy with localhost API settings.

## Pages and access

- `/login` and `/register`: customer authentication. Agents and administrators use the same sign-in page.
- `/guest`: start a support conversation without registering; the visitor session is kept in the current browser tab.
- `/`: authenticated customers start conversations and see their own conversation history.
- `/chat/:id`: authenticated customer chat with live WebSocket messaging and message history.
- `/inbox` and `/inbox/:id`: agent inbox, assigned conversations, live replies, and AI takeover/handback.
- `/admin`: administrator conversation assignment, closure/deletion, agent management, and the RAG knowledge library.

Use the **Knowledge** tab to upload company PDF, TXT, and Markdown files (up to 10 MB). The API extracts and indexes the text; original files are not retained. Uploaded documents can be removed from the same tab, which deletes their PostgreSQL source chunks and Qdrant vectors.

The customer inbox calls the authenticated `GET /chat/rooms` endpoint, which returns only the signed-in customer's rooms. Session credentials are kept in `sessionStorage` for the active browser tab and are cleared on sign-out or unauthorized API responses. Protect the site against cross-site scripting and configure HTTPS in production. The current WebSocket API authenticates using its existing token query parameter.
