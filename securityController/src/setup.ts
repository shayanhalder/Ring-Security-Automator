import type { BrowserContext } from 'playwright';
import { chromium } from 'playwright';
import fs from 'fs';
import { login } from './authentication';

export async function initializeBrowser(accountDashboardURL: string, loginURL: string, email: string, password: string, headlessMode: boolean) {
    const browser = await chromium.launch({ headless: headlessMode });
    let context: BrowserContext;
    // check if session.json exists and load it if available
    if (fs.existsSync('session.json')) {
        console.log('Loading saved session cookies from session.json...');
        context = await browser.newContext({
            storageState: 'session.json'  // This loads cookies and localStorage from session.json
        });
    } else {
        console.log('No saved session cookies found, creating new context...');
        context = await browser.newContext();
    }
    
    const page = await context.newPage();    

    // attempt navigating to the account dashboard and wait 4 seconds
    await page.goto(accountDashboardURL);
    await new Promise(resolve => setTimeout(resolve, 4000));

    const currentUrl = page.url();
    console.log('Current URL after navigation:', currentUrl);

    // if our session cookies expired, then we will automatically be redirected to the login page
    if (currentUrl !== accountDashboardURL) {
        console.log('Not logged in, starting login process...');
        await login(page, email, password, loginURL);

        await page.goto(accountDashboardURL);
        await context.storageState({ path: 'session.json' });
        console.log('Session saved to session.json');
    }

    return { initialBrowser: browser, initialContext: context, initialPage: page };

}
