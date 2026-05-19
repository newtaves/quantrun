// API Server configurations
export const DJANGO_API_URL = import.meta.env.VITE_DJANGO_API_URL || "http://localhost:8000";
export const FASTAPI_API_URL = import.meta.env.VITE_FASTAPI_API_URL || "http://localhost:8000"; // Note: FastAPI could run on 8000 or 8001 depending on your dev startup, we'll connect dynamically!
export const FASTAPI_WS_URL = import.meta.env.VITE_FASTAPI_WS_URL || "ws://localhost:8000";

// Standard helper to resolve FastAPI ports/hosts dynamically if clashing
export const getFastApiUrl = () => {
  // If FastAPI is running on a different port, e.g. 8000, we fallback or use the config
  return FASTAPI_API_URL;
};
