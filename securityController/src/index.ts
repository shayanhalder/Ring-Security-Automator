import type { Page } from 'playwright';
import express from 'express';
import { initializeBrowser } from './setup';
import { armSecurityAway, disarmSecurity, armSecurityHome } from './ringSecurityControllers';
import dotenv from 'dotenv';

dotenv.config();

const email = process.env.EMAIL;
const password = process.env.PASSWORD;
const loginURL = process.env.LOGIN_URL;
const accountDashboardURL = process.env.ACCOUNT_DASHBOARD_URL;
const headlessMode = process.env.HEADLESS_MODE === 'true';

if (!email || !password || !loginURL || !accountDashboardURL) {
    console.error('EMAIL or PASSWORD or LOGIN_URL or ACCOUNT_DASHBOARD_URL is not set');
    process.exit(1);
}

const app = express();
const port = 3000;

let page: Page;

app.get('/', async (_req, res) => {
    try {
        console.log("Received test request to root route")
        res.send('Ring Security Client active and running');
    } catch (error) {
        console.error('Error in route handler:', error);
        res.status(500).send({
            'success': false,
            'message': 'Internal server error: ' + error
        });
    }
});

app.get('/arm-security-away', async (_req, res) => {
    if (!page) {
        console.error('Page not initialized');
        res.status(500).send({
            'success': false,
            'message': 'Internal server error: Page object is not initialized' 
        });
    }
    try {
        console.log("Received request to arm security away...")
        await armSecurityAway(page, password, accountDashboardURL);
        res.status(200).send({
            'success': true,
            'message': 'Armed security away successfully'
        });
    } catch (error) {
        console.error('Error in route handler:', error);
        res.status(500).send({
            'success': false,
            'message': 'Internal server error: ' + error
        });
    }
});

app.get('/disarm-security', async (_req, res) => {
    if (!page) {
        console.error('Page not initialized');
        res.status(500).send({
            'success': false,
            'message': 'Internal server error: Page object is not initialized'
        });
        return;
    }
    try {
        console.log("Received request to disarm security...")
        await disarmSecurity(page, password, accountDashboardURL);
        res.status(200).send({
            'success': true,
            'message': 'Disarmed security successfully'
        });
    } catch (error) {
        console.error('Error in route handler:', error);
        res.status(500).send({
            'success': false,
            'message': 'Internal server error: ' + error
        });
    }
});

app.get('/arm-security-home', async (_req, res) => {
    if (!page) {
        console.error('Page not initialized');
        res.status(500).send({
            'success': false,
            'message': 'Internal server error: Page object is not initialized'
        });
        return;
    }
    try {
        console.log("Received request to arm security home...")
        await armSecurityHome(page, password, accountDashboardURL);
        res.status(200).send({
            'success': true,
            'message': 'Armed security home successfully'
        });
    } catch (error) {
        console.error('Error in route handler:', error);
        res.status(500).send({
            'success': false,
            'message': 'Internal server error: ' + error
        });
    }
});

app.listen(port, async () => {
    console.log(`Server is running on port ${port}`);

    console.log('Email:', email);
    console.log('Password:', password);
    console.log('Login URL:', loginURL);
    console.log('Account Dashboard URL:', accountDashboardURL);

    try {
        const { initialPage } = await initializeBrowser(accountDashboardURL, loginURL, email, password, headlessMode);
        page = initialPage;

    } catch (error) {
        console.error('Failed to initialize browser:', error);
    }
});

