import type { Page } from 'playwright';
import readline from 'readline';

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

    // after entering password, we are prompted to enter the one-time code
    const onetimecodeInput = page.frameLocator('iframe').locator('#one-time-code');
    const staySignedInCheckbox = page.frameLocator('iframe').locator('#trustBrowser'); // stays signed in for 90 days
    submitButton = page.frameLocator('iframe').locator('button[data-testid="submit-button-final-sign-in-card"]');

    onetimecodeInput.waitFor();

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    await new Promise<void>((resolve) => { // prompt the user for the one-time code
      rl.question('Enter your one-time code: ', async (code: string) => {
        await onetimecodeInput.fill(code.trim());
        rl.close();
        resolve();
      });
    });

    staySignedInCheckbox.waitFor();
    await staySignedInCheckbox.click();

    submitButton.waitFor();
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
