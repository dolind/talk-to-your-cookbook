import {createContext, useContext, useEffect, useState} from 'react';
import api, {deleteTokens, getTokens, saveTokens} from '../utils/api'; // assumes axios instance with baseURL
// No need for setAuthToken if using cookies
import {components} from "../types/api";

// Define recipe type
type UserResponse = components["schemas"]["UserResponse"];
type UserCreate = components["schemas"]["UserCreate"];
type UserUpdate = components["schemas"]["UserUpdate"];


type AuthContextType = {
    user: UserResponse | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    register: (data: UserCreate) => Promise<void>;
    updateUser: (data: Partial<UserUpdate>) => Promise<void>;
};


const AuthContext = createContext<AuthContextType | undefined>(undefined);


export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({children}) => {
    const [user, setUser] = useState<UserResponse | null>(null);
    const [loading, setLoading] = useState(true);

    // 🔹 Load user if tokens exist
    useEffect(() => {
        const initAuth = async () => {
            const tokens = await getTokens();
            if (!tokens?.access_token) {
                setLoading(false);
                return;
            }

            api.defaults.headers.common.Authorization = `Bearer ${tokens.access_token}`;

            try {
                const {data} = await api.get<UserResponse>('/users/me');
                setUser(data);
            } catch {
                setUser(null);
            } finally {
                setLoading(false);
            }
        };
        initAuth();
    }, []);

    const login = async (email: string, password: string) => {
        const params = new URLSearchParams();
        params.append('username', email);
        params.append('password', password);

        const {data} = await api.post('/auth/token', params, {
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        });

        await saveTokens({
            access_token: data.access_token,
            refresh_token: data.refresh_token,
        });

        api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;

        const res = await api.get<UserResponse>('/users/me');
        setUser(res.data);
    };

    const register = async (data: UserCreate) => {
        const res = await api.post('/auth/register', data);

        await saveTokens({
            access_token: res.data.access_token,
            refresh_token: res.data.refresh_token,
        });

        api.defaults.headers.common.Authorization = `Bearer ${res.data.access_token}`;
        const userRes = await api.get<UserResponse>('/users/me');
        setUser(userRes.data);
    };

    const logout = async () => {
        await deleteTokens();
        setUser(null);
    };

    const updateUser = async (data: Partial<UserUpdate>) => {
        const res = await api.put<UserResponse>('/users/me', data);
        setUser(res.data);
    };

    return (
        <AuthContext.Provider value={{user, loading, login, register, logout, updateUser}}>
            {!loading && children}
        </AuthContext.Provider>
    );
};


export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error('useAuth must be used within an AuthProvider');
    return context;
};
