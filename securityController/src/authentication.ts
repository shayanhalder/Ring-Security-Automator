import type { Page } from 'playwright';
import readline from 'readline';
import { isTwilioOtpEnabled, requestOtpCode } from './twilioOtpService';

async function promptOtpFromStdin(): Promise<string> {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
    });

    return new Promise((resolve) => {
        rl.question('Enter your one-time code: ', (code: string) => {
            rl.close();
            resolve(code.trim());
        });
    });
}

async function resolveOtpCode(): Promise<string> {
    if (isTwilioOtpEnabled()) {
        return requestOtpCode();
    }

    console.log('[OTP] Twilio not configured, prompting from stdin');
    return promptOtpFromStdin();
}

// login page with no email default
export async function login(page: Page, email: string, password: string, loginURL: string) {
    await page.goto(loginURL);

    const emailInput = page.frameLocator('iframe').locator('input[aria-label="Enter your email address"]');
    let submitButton = page.frameLocator('iframe').locator('button[data-testid="submit-button-final-sign-in-card"]');

    await emailInput.waitFor();
    await emailInput.fill(email);
    
    await submitButton.waitFor();
    await submitButton.click(); // "continue" button to go to password page

    const passwordInput = page.frameLocator('iframe').locator('input[aria-label="Enter your password"]');
    submitButton = page.frameLocator('iframe').locator('button[data-testid="submit-button-final-sign-in-card"]');

    await passwordInput.waitFor();
    await passwordInput.fill(password);
    
    await submitButton.waitFor();
    await submitButton.click(); // "continue" button to go to one-time code page

    await new Promise(resolve => setTimeout(resolve, 4000));

    // Check for "Got it" button and click if present
    const gotItButton = page.locator('button', { hasText: 'Got it' });
    if (await gotItButton.isVisible().catch(() => false)) {
        console.log('[INFO] "Got it" button found, clicking...');
        await gotItButton.click();
        await new Promise(resolve => setTimeout(resolve, 1000)); // allow UI time to update
    }

    await page.screenshot({ path: 'after-password-headless.png', fullPage: true });

    for (const frame of page.frames()) {
        console.log('[DEBUG] Frame URL:', frame.url());
    }

    const usiHtml = await page.frameLocator('iframe#usiIFrame').locator('html').innerHTML();

    const containsOneTimeCode = /id\s*=\s*("|')one-time-code\1/.test(usiHtml);
    console.log(containsOneTimeCode);

    const containsAnotherIframe = /<iframe\b(?![^>]*id\s*=\s*("|')usiIFrame\1)/.test(usiHtml);
    console.log(containsAnotherIframe);

    // after entering password, we are prompted to enter the one-time code
    const otpFrame = page.frameLocator('iframe#usiIFrame');
    // const onetimecodeInput = otpFrame.locator('#one-time-code');
    const onetimecodeInput = otpFrame.locator('input[aria-label="Enter the 6-digit code you received"]');
    
    const staySignedInCheckbox = otpFrame.locator('#trustBrowser'); // stays signed in for 90 days
    submitButton = otpFrame.locator('button[data-testid="submit-button-final-sign-in-card"]');

    // Print the HTML of the current page for debugging purposes
    // const html = await page.content();
    // Instead of console.log, write the current page HTML to "login_page.html"
    // and also write the iframe's HTML content to "iframe.html"

    // fs.writeFileSync('login_page.html', html);
    // fs.writeFileSync('iframe.html', usiHtml);

    try { // OTP only needed ocasionally once our cookies expire 
        await onetimecodeInput.waitFor({ state: 'attached', timeout: 20000 }); // 20s timeout, adjust as needed
    } catch (error) {
        console.log('[OTP] One-time code input did not appear.');
        return;
    }

    const code = await resolveOtpCode();
    await onetimecodeInput.fill(code);

    await staySignedInCheckbox.waitFor();
    await staySignedInCheckbox.click();

    await submitButton.waitFor();
    await submitButton.click(); // "continue" button to go to account dashboard

    await new Promise(resolve => setTimeout(resolve, 2000)); // wait 2 seconds
}

export async function handleReloginPrompt(page: Page, password: string) {
    const passwordInput = page.frameLocator('iframe[title="Verify your account"]').locator('#password');
    await passwordInput.fill(password);

    const reloginSubmitButton = page.frameLocator('iframe[title="Verify your account"]').locator('button[type="submit"].challenge-password-button.captcha-trigger');
    await reloginSubmitButton.click();

    await new Promise(resolve => setTimeout(resolve, 2000)); // wait 2 seconds
}

export async function checkReloginPrompt(page: Page) : Promise<boolean> {
    const iframeLocator = page.locator('iframe[title="Verify your account"]');
    const iframeCount = await iframeLocator.count();
    const hasChallengeIframe = iframeCount > 0;
    return hasChallengeIframe;
}
