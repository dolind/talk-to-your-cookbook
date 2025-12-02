import {useCallback, useState} from 'react';
import api from '../../../utils/api';
import {Recipe, RecipePage} from '../types';

export const useRecipeSearch = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Recipe[]>([]);

    const search = useCallback(async (term: string) => {
        setQuery(term);
        if (!term.trim()) {
            setResults([]);
            return;
        }

        try {
            const {data} = await api.get<RecipePage>(`/recipes`, {
                params: {search: term, limit: 20},
                withCredentials: true,
            });
            setResults(data.items as Recipe[]);
        } catch (error) {
            console.error('Recipe search failed', error);
            setResults([]);
        }
    }, []);

    return {query, results, search};
};
