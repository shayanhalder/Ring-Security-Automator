import type { Page } from 'playwright';
import { handleReloginPrompt, checkReloginPrompt } from './authentication';

export enum SecurityStatus {
    AWAY = 'Away',
    DISARMED = 'Disarmed',
    HOME = 'Home',
    UNKNOWN = 'Unknown',
}

export async function armSecurityAway(page: Page, password: string, accountDashboardURL: string) {
    const armButton = page.locator('div[aria-label="To arm & set to away mode, press this button."]');
    await armButton.waitFor();
    await armButton.click();

    await new Promise(resolve => setTimeout(resolve, 2000));

    const reloginPrompt = await checkReloginPrompt(page);

    if (reloginPrompt) {
        console.log('Detecting relogin prompt, handling reauthentication...');
        await handleReloginPrompt(page, password);

        // after relogging in, check to see if we can navigate to the account dashboard

        await page.goto(accountDashboardURL);
        await new Promise(resolve => setTimeout(resolve, 2000));

        const currentUrl = page.url();
        console.log('Current URL after navigation:', currentUrl);

    }

    const backToDashboardButton = page.getByRole('button', { name: 'Back to Dashboard' });

    if (await backToDashboardButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await backToDashboardButton.click();
    } else {
        console.log('Back to dashboard button not found, continuing...');
    }
}

export async function disarmSecurity(page: Page, password: string, accountDashboardURL: string) {
    const disarmButton = page.locator('div[aria-label="To disarm your Ring Alarm system, press this button."]');
    await disarmButton.waitFor();
    await disarmButton.click();

    // To disarm your Ring Alarm system, press this button.

    await new Promise(resolve => setTimeout(resolve, 2000));

    const reloginPrompt = await checkReloginPrompt(page);

    if (reloginPrompt) {
        console.log('Detecting relogin prompt, handling reauthentication...');
        await handleReloginPrompt(page, password);

        // after relogging in, check to see if we can navigate to the account dashboard

        await page.goto(accountDashboardURL);
        await new Promise(resolve => setTimeout(resolve, 2000));

        const currentUrl = page.url();
        console.log('Current URL after navigation:', currentUrl);

    }

    const backToDashboardButton = page.getByRole('button', { name: 'Back to Dashboard' });
    
    if (await backToDashboardButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await backToDashboardButton.click();
    } else {
        console.log('Back to dashboard button not found, continuing...');
    }
}

export async function armSecurityHome(page: Page, password: string, accountDashboardURL: string) {
    const armSecurityHomeButton = page.locator('div[aria-label="To arm & set to home mode, press this button."]');
    await armSecurityHomeButton.waitFor();
    await armSecurityHomeButton.click();

    await new Promise(resolve => setTimeout(resolve, 2000));

    const reloginPrompt = await checkReloginPrompt(page);

    if (reloginPrompt) {
        console.log('Detecting relogin prompt, handling reauthentication...');
        await handleReloginPrompt(page, password);

        // after relogging in, check to see if we can navigate to the account dashboard

        await page.goto(accountDashboardURL);
        await new Promise(resolve => setTimeout(resolve, 2000));

        const currentUrl = page.url();
        console.log('Current URL after navigation:', currentUrl);

    }

    const backToDashboardButton = page.getByRole('button', { name: 'Back to Dashboard' });
    
    if (await backToDashboardButton.isVisible({ timeout: 3000 }).catch(() => false)) {
        await backToDashboardButton.click();
    } else {
        console.log('Back to dashboard button not found, continuing...');
    }
}


export async function getSecurityStatus(page: Page) {
    const securityStatus = page.locator('p#alarm-mode-label');
    await securityStatus.waitFor();

    const securityStatusText = await securityStatus.textContent();

    if (securityStatusText === SecurityStatus.AWAY) {
        return SecurityStatus.AWAY;
    } else if (securityStatusText === SecurityStatus.DISARMED) {
        return SecurityStatus.DISARMED;
    } else if (securityStatusText === SecurityStatus.HOME) {
        return SecurityStatus.HOME;
    } else {
        return SecurityStatus.UNKNOWN;
    }
}


