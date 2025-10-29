import * as fs from 'fs';
import * as path from 'path';

interface Cookie {
  name: string;
  value: string;
  domain: string;
  path: string;
  expires: number;
  httpOnly: boolean;
  secure: boolean;
  sameSite: string;
}

interface SessionData {
  cookies: Cookie[];
  origins: any[];
}

// Read the session.json file
const sessionPath = path.join(__dirname, '..', 'session.json');
const sessionData: SessionData = JSON.parse(fs.readFileSync(sessionPath, 'utf-8'));

console.log('Cookie Expiration Dates:\n');

sessionData.cookies.forEach((cookie, i) => {
  let dateStr: string;
  let timeStr: string;
  
  if (cookie.expires === -1) {
    dateStr = 'Session cookie';
    timeStr = 'No expiration';
  } else {
    const date = new Date(Math.floor(cookie.expires) * 1000);
    dateStr = date.toLocaleDateString('en-US', { 
      month: '2-digit', 
      day: '2-digit', 
      year: 'numeric' 
    });
    timeStr = date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }
  
  console.log(`${(i + 1).toString().padStart(2)}. ${cookie.name}`);
  console.log(`    Expires: ${dateStr} ${timeStr}`);
  console.log(`    Domain: ${cookie.domain}`);
  console.log();
});
