/**
 * Utility to get the server IP address from the API endpoint
 */

let cachedIp: string | null = null;

export async function getServerIp(): Promise<string> {
  // Return cached IP if available
  if (cachedIp) {
    return cachedIp;
  }

  try {
    const response = await fetch('/api/ip');
    const data = await response.json();
    cachedIp = data.ip;
    return cachedIp;
  } catch (error) {
    console.error('Error fetching IP from API:', error);
    // Fallback to target PC IP (update this to the deployment machine's IP)
    return '192.168.10.2';
  }
}

export function getWebSocketUrl(port: number = 6790): Promise<string> {
  return getServerIp().then(ip => `ws://${ip}:${port}`);
}



