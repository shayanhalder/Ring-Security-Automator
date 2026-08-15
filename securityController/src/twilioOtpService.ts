import twilio from 'twilio';

function getPollIntervalMs(): number {
    const value = process.env.OTP_POLL_INTERVAL_MS;
    return value ? parseInt(value, 10) : 2000;
}

function getTimeoutMs(): number {
    const value = process.env.OTP_TIMEOUT_MS;
    return value ? parseInt(value, 10) : 300000;
}

export function isTwilioOtpEnabled(): boolean {
    return process.env.ENABLE_TWILIO_OTP === 'true';
}

function getTwilioClient() {
    const accountSid = process.env.TWILIO_ACCOUNT_SID!;
    const authToken = process.env.TWILIO_AUTH_TOKEN!;
    return twilio(accountSid, authToken);
}

function parseOtpFromBody(body: string | null | undefined): string | null {
    if (!body) {
        return null;
    }

    const trimmed = body.trim();
    const sixDigitMatch = trimmed.match(/\b(\d{6})\b/);
    if (sixDigitMatch) {
        return sixDigitMatch[1];
    }

    if (/^\d+$/.test(trimmed)) {
        return trimmed;
    }

    return null;
}

function normalizePhone(phone: string): string {
    return phone.replace(/\s/g, '');
}

async function sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function requestOtpCode(): Promise<string> {
    if (!isTwilioOtpEnabled()) {
        throw new Error('Twilio OTP is not configured');
    }

    const client = getTwilioClient();
    const twilioPhoneNumber = normalizePhone(process.env.TWILIO_PHONE_NUMBER!);
    const otpPhoneNumber = normalizePhone(process.env.OTP_PHONE_NUMBER!);
    const pollIntervalMs = getPollIntervalMs();
    const timeoutMs = getTimeoutMs();

    const requestSentAt = new Date();

    console.log('[OTP] Sending SMS request for one-time code...');
    await client.messages.create({
        body: 'Ring login needs your one-time code. Reply with the 6-digit code.',
        from: twilioPhoneNumber,
        to: otpPhoneNumber,
    });

    const deadline = Date.now() + timeoutMs;

    while (Date.now() < deadline) {
        const messages = await client.messages.list({
            from: otpPhoneNumber,
            to: twilioPhoneNumber,
            dateSentAfter: requestSentAt,
            limit: 10,
        });

        for (const message of messages) {
            if (message.direction !== 'inbound') {
                continue;
            }

            const code = parseOtpFromBody(message.body);
            if (code) {
                console.log('[OTP] Received one-time code via SMS');
                return code;
            }
        }

        await sleep(pollIntervalMs);
    }

    throw new Error(`Timed out waiting for OTP SMS reply after ${timeoutMs / 1000}s`);
}
