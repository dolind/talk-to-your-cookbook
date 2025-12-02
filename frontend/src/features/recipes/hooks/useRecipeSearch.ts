import {useCallback, useEffect, useRef, useState} from 'react';
import {useInView} from 'react-intersection-observer';
import qs from 'qs';
import api from '../../../utils/api';
import {INITIAL_FILTERS, RecipeFilterOptions, RecipeFilters, RecipePage, RecipeRead, SortOrder} from '../types';

const PAGE_SIZE = 20;

export const useRecipeSearch = () => {
    const [filters, setFilters] = useState<RecipeFilters>(INITIAL_FILTERS);
    const [recipes, setRecipes] = useState<RecipeRead[]>([]);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true);
    const [loading, setLoading] = useState(false);
    const [availableCategories, setAvailableCategories] = useState<string[]>([]);
    const [availableSources, setAvailableSources] = useState<string[]>([]);

    const {ref: loadMoreRef, inView} = useInView({rootMargin: '1000px'});

    const fetchFilters = useCallback(async () => {
        try {
            const res = await api.get<RecipeFilterOptions>('/recipes/filters', {withCredentials: true});
            setAvailableCategories(res.data.categories ?? []);
            setAvailableSources(res.data.sources ?? []);
        } catch (error) {
            console.error('Failed to fetch filters', error);
        }
    }, []);

    useEffect(() => {
        void fetchFilters();
    }, [fetchFilters]);

    const fetchRecipes = useCallback(async (pageToFetch: number, activeFilters: RecipeFilters) => {
        setLoading(true);

        try {
            const res = await api.get<RecipePage>('/recipes/infinite', {
                params: {
                    page: pageToFetch,
                    pageSize: PAGE_SIZE,
                    sort: activeFilters.sort,
                    categories: activeFilters.categories,
                    tags: activeFilters.tags,
                    source: activeFilters.source,
                    maxTime: activeFilters.maxTime,
                    search: activeFilters.search,
                },
                paramsSerializer: params => qs.stringify(params, {arrayFormat: 'repeat'}),
                withCredentials: true,
            });

            const newRecipes = res.data.items ?? [];

            setRecipes(prev => {
                const merged = pageToFetch === 1 ? newRecipes : [...prev, ...newRecipes];
                return Array.from(new Map(merged.map(r => [r.id, r])).values());
            });

            setHasMore(res.data.hasMore ?? false);
            setPage(pageToFetch + 1);
        } catch (error) {
            console.error('Failed to fetch recipes', error);
        } finally {
            setLoading(false);
        }
    }, []);


    useEffect(() => {
        setRecipes([]);
        setPage(1);
        setHasMore(true);
        window.scrollTo({top: 0, behavior: 'smooth'});
        void fetchRecipes(1, filters);
    }, [filters, fetchRecipes]);

    const isFetchingRef = useRef(false);

    const fetchNextPage = useCallback(() => {
        if (loading || !hasMore || isFetchingRef.current) {
            return;
        }
        isFetchingRef.current = true;
        void fetchRecipes(page, filters).finally(() => {
            isFetchingRef.current = false;
        });
    }, [fetchRecipes, filters, hasMore, loading, page]);

    useEffect(() => {
        if (inView) {
            fetchNextPage();
        }
    }, [fetchNextPage, inView]);

    const setSearchTerm = useCallback((value: string) => {
        setFilters(prev => ({...prev, search: value}));
    }, []);

    const setCategories = useCallback((categories: string[]) => {
        setFilters(prev => ({...prev, categories}));
    }, []);

    const setTags = useCallback((tags: string[]) => {
        setFilters(prev => ({...prev, tags}));
    }, []);

    const setSource = useCallback((source: string) => {
        setFilters(prev => ({...prev, source}));
    }, []);

    const setMaxTime = useCallback((maxTime: number | '') => {
        setFilters(prev => ({...prev, maxTime}));
    }, []);

    const setSortOrder = useCallback((sort: SortOrder) => {
        setFilters(prev => ({...prev, sort}));
    }, []);

    const clearFilters = useCallback(() => {
        setFilters(prev => ({...prev, categories: [], tags: [], source: '', maxTime: ''}));
    }, []);

    const removeRecipesById = useCallback((ids: string[]) => {
        setRecipes(prev => prev.filter(recipe => !ids.includes(recipe.id)));
    }, []);

    return {
        filters,
        recipes,
        hasMore,
        loading,
        availableCategories,
        availableSources,
        loadMoreRef,
        setSearchTerm,
        setCategories,
        setTags,
        setSource,
        setMaxTime,
        setSortOrder,
        clearFilters,
        removeRecipesById,
    };
};
