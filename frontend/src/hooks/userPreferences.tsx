import {useState} from 'react';
import api from '../utils/api';

export const userPreferences = () => {
    const [prefs, setPrefs] = useState(null);

    const fetchPreferences = async () => {
        const res = await api.get('/users/me/preferences');
        setPrefs(res.data);
    };

    const updatePreferences = async (updates: any) => {
        const res = await api.put('/users/me/preferences', updates);
        setPrefs(res.data);
    };


    return {prefs, updatePreferences};
};
