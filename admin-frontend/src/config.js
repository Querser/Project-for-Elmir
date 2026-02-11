export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').toString().trim();

export const ADMIN_AUTH_PREFIX =
  (import.meta.env.VITE_ADMIN_AUTH_PREFIX ?? '/api/v1/admin/auth').toString().trim();

export const TRAININGS_PREFIX =
  (import.meta.env.VITE_TRAININGS_PREFIX ?? '/api/v1/trainings').toString().trim();

export const LOCATIONS_PREFIX =
  (import.meta.env.VITE_LOCATIONS_PREFIX ?? '/api/v1/locations').toString().trim();
