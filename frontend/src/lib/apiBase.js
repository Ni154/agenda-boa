// src/lib/apiBase.js — compatível com REACT_APP_API_BASE_URL (ou BACKEND_URL)
const RAW =
  process.env.REACT_APP_API_BASE_URL ||
  process.env.REACT_APP_BACKEND_URL ||
  '/';

// Se vier '/api', usamos direto; se vier '/', cai em '/api'; se vier URL completa, anexamos /api.
export const API_BASE =
  RAW.startsWith('/api') ? RAW : (RAW === '/' ? '/api' : `${RAW.replace(/\/$/, '')}/api`);
