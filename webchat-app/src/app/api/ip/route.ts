import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    // Read ip.txt from the Black-Jack directory
    // If process.cwd() is .../Black-Jack/webchat-app, then ../ip.txt is .../Black-Jack/ip.txt
    const ipFilePath = path.join(process.cwd(), '..', 'ip.txt');
    
    // Try to read the file
    const ip = fs.readFileSync(ipFilePath, 'utf-8').trim();
    
    // Clean up the IP (remove http://, https://, and port if present)
    let cleanIp = ip.replace(/^https?:\/\//, '').split(':')[0].trim();
    
    return NextResponse.json({ ip: cleanIp });
  } catch (error) {
    // Fallback to target PC IP if file not found
    console.error('Error reading ip.txt:', error);
    return NextResponse.json({ ip: '192.168.10.2' }, { status: 200 });
  }
}



