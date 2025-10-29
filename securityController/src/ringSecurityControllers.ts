import type { Page } from 'playwright';
import { handleReloginPrompt, checkReloginPrompt } from './authentication';

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

        const armButton = page.locator('div[aria-label="To arm & set to away mode, press this button."]');
        await armButton.waitFor();
        await armButton.click();
    }
}

export async function disarmSecurity(page: Page, password: string, accountDashboardURL: string) {
    const disarmButton = page.locator('div[aria-label="To disarm & set to home mode, press this button."]');
    await disarmButton.waitFor();
    await disarmButton.click();

    const reloginPrompt = await checkReloginPrompt(page);

    if (reloginPrompt) {
        console.log('Detecting relogin prompt, handling reauthentication...');
        await handleReloginPrompt(page, password);

        // after relogging in, check to see if we can navigate to the account dashboard

        await page.goto(accountDashboardURL);
        await new Promise(resolve => setTimeout(resolve, 2000));

        const currentUrl = page.url();
        console.log('Current URL after navigation:', currentUrl);

        const disarmButton = page.locator('div[aria-label="To disarm & set to home mode, press this button."]');
        await disarmButton.waitFor();
        await disarmButton.click();
    }
}

export async function armSecurityHome(page: Page, password: string, accountDashboardURL: string) {
    const armSecurityHomeBUtton = page.locator('div[aria-label="To arm & set to home mode, press this button."]');
    await armSecurityHomeBUtton.waitFor();
    await armSecurityHomeBUtton.click();

    const reloginPrompt = await checkReloginPrompt(page);

    if (reloginPrompt) {
        console.log('Detecting relogin prompt, handling reauthentication...');
        await handleReloginPrompt(page, password);

        // after relogging in, check to see if we can navigate to the account dashboard

        await page.goto(accountDashboardURL);
        await new Promise(resolve => setTimeout(resolve, 2000));

        const currentUrl = page.url();
        console.log('Current URL after navigation:', currentUrl);

        const armSecurityHomeBUtton = page.locator('div[aria-label="To arm & set to away mode, press this button."]');
        await armSecurityHomeBUtton.waitFor();
        await armSecurityHomeBUtton.click();
    }
}

