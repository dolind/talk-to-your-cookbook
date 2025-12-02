// utils/api.ts
import axios from 'axios';


const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL, // adjust as needed
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
});

export function saveTokens(tokens: { access_token: string; refresh_token: string }) {
    localStorage.setItem('tokens', JSON.stringify(tokens));
}

export function getTokens(): { access_token: string; refresh_token: string } | null {
    const raw = localStorage.getItem('tokens');
    return raw ? JSON.parse(raw) : null;
}

export function deleteTokens() {
    localStorage.removeItem('tokens');
}


api.interceptors.request.use((config) => {
    const tokens = getTokens();
    if (tokens?.access_token) {
        config.headers.Authorization = `Bearer ${tokens.access_token}`;
    }
    return config;
});

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const original = error.config;

        if (error.response?.status === 401 && !original._retry) {
            original._retry = true;
            const tokens = getTokens();

            if (!tokens?.refresh_token) {
                console.warn('No refresh token — logging out.');
                deleteTokens();
                return Promise.reject(error);
            }

            try {
                const {data} = await axios.post(`${api.defaults.baseURL}/auth/refresh`, {
                    refresh_token: tokens.refresh_token,
                });

                const newTokens = {
                    access_token: data.access_token,
                    refresh_token: data.refresh_token,
                };
                saveTokens(newTokens);

                api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
                original.headers.Authorization = `Bearer ${data.access_token}`;

                return api(original);
            } catch (refreshErr) {
                console.error('Token refresh failed', refreshErr);
                deleteTokens();
                return Promise.reject(refreshErr);
            }
        }

        return Promise.reject(error);
    }
);

export async function authFetch(
    input: string,
    init: RequestInit = {}
): Promise<Response> {
    const tokens = getTokens();
    const headers = new Headers(init.headers || {});
    headers.set('Content-Type', 'application/json');

    if (tokens?.access_token) {
        headers.set('Authorization', `Bearer ${tokens.access_token}`);
    }

    const response = await fetch(input, {...init, headers});

    // If token expired, try refresh once
    if (response.status === 401 && tokens?.refresh_token) {
        try {
            const refreshRes = await fetch(`${api.defaults.baseURL}/auth/refresh`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({refresh_token: tokens.refresh_token}),
            });

            if (!refreshRes.ok) throw new Error('Refresh failed');
            const data = await refreshRes.json();

            const newTokens = {
                access_token: data.access_token,
                refresh_token: data.refresh_token,
            };
            saveTokens(newTokens);

            // Retry the original request with new token
            headers.set('Authorization', `Bearer ${newTokens.access_token}`);
            return fetch(input, {...init, headers});
        } catch (err) {
            console.error('Token refresh failed during authFetch', err);
            deleteTokens();
            throw err;
        }
    }

    return response;
}


export default api;
