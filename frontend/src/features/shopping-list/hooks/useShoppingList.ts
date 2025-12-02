import {useCallback, useEffect, useMemo, useState} from 'react';
import api from '../../../utils/api';
import {ShoppingListItem, ShoppingListItemCreate, ShoppingListItemUpdate, ShoppingListRead,} from '../types';

export const useShoppingList = () => {
    const [shoppingList, setShoppingList] = useState<ShoppingListRead | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchShoppingList = useCallback(async () => {
        setLoading(true);
        try {
            const {data} = await api.get<ShoppingListRead>(`/shoppinglist`, {
                withCredentials: true,
            });
            setShoppingList(data);
        } catch (error) {
            console.error('Failed to load shopping list', error);
            setShoppingList(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        void fetchShoppingList();
    }, [fetchShoppingList]);

    const recipeTitleMap = useMemo(() => {
        if (!shoppingList?.imported_recipes) return {} as Record<string, string>;
        return Object.fromEntries(
            shoppingList.imported_recipes.map(recipe => [recipe.recipe_id, recipe.title]),
        );
    }, [shoppingList?.imported_recipes]);

    const toggleChecked = useCallback(
        async (itemId: string) => {
            if (!shoppingList) return;
            const target = shoppingList.items.find(item => item.id === itemId);
            if (!target) return;

            const updated = {...target, checked: !target.checked};
            const payload: ShoppingListItemUpdate = {checked: updated.checked ?? false};

            try {
                await api.patch<ShoppingListItem>(`/shoppinglist/items/${itemId}`, payload, {
                    withCredentials: true,
                });
                setShoppingList(prev =>
                    prev
                        ? {...prev, items: prev.items.map(item => (item.id === itemId ? updated : item))}
                        : prev,
                );
            } catch (error) {
                console.error('Toggle failed', error);
            }
        },
        [shoppingList],
    );

    const deleteItem = useCallback(async (itemId: string) => {
        try {
            await api.delete(`/shoppinglist/items/${itemId}`, {withCredentials: true});
            setShoppingList(prev =>
                prev ? {...prev, items: prev.items.filter(item => item.id !== itemId)} : prev,
            );
        } catch (error) {
            console.error('Delete failed', error);
        }
    }, []);

    const addItem = useCallback(async (ingredient: string) => {
        if (!ingredient.trim()) return;
        try {
            const payload: ShoppingListItemCreate = {
                ingredient_name: ingredient.trim(),
                quantity: null,
                unit: null,
            };
            const {data} = await api.post<ShoppingListItem>(`/shoppinglist/items`, payload, {
                withCredentials: true,
            });
            setShoppingList(prev =>
                prev ? {...prev, items: [...prev.items, data]} : prev,
            );
        } catch (error) {
            console.error('Add failed', error);
        }
    }, []);

    const clearAll = useCallback(async () => {
        try {
            await api.delete(`/shoppinglist`, {withCredentials: true});
            await fetchShoppingList();
        } catch (error) {
            console.error('Clear failed', error);
        }
    }, [fetchShoppingList]);

    const removeRecipe = useCallback(
        async (recipeId: string) => {
            try {
                await api.delete(`/shoppinglist/by-recipe/${recipeId}`, {withCredentials: true});
                await fetchShoppingList();
            } catch (error) {
                console.error('Failed to remove recipe', error);
            }
        },
        [fetchShoppingList],
    );

    const removeMealPlan = useCallback(
        async (mealPlanId: string) => {
            try {
                await api.delete(`/shoppinglist/by-meal-plan/${mealPlanId}`, {withCredentials: true});
                await fetchShoppingList();
            } catch (error) {
                console.error('Failed to remove meal plan', error);
            }
        },
        [fetchShoppingList],
    );

    return {
        shoppingList,
        loading,
        recipeTitleMap,
        fetchShoppingList,
        toggleChecked,
        deleteItem,
        addItem,
        clearAll,
        removeRecipe,
        removeMealPlan,
    };
};
