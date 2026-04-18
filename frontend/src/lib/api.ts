/**
 * Central API configuration.
 * In production, set NEXT_PUBLIC_API_URL to your Railway backend URL.
 * Locally it falls back to http://localhost:8000.
 */
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** REST API base URL — e.g. https://your-backend.up.railway.app */
export const API_URL = BASE_URL;

/**
 * WebSocket URL — automatically switches between:
 *   ws://  for local HTTP development
 *   wss:// for deployed HTTPS (required by browsers on secure origins)
 */
export const getWsUrl = (campaignId: string): string => {
  const wsBase = BASE_URL
    .replace(/^https:\/\//, 'wss://')
    .replace(/^http:\/\//, 'ws://');
  return `${wsBase}/ws/game/${campaignId}`;
};
