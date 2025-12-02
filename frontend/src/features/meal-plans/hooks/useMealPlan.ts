import {useCallback, useEffect, useMemo, useState} from 'react';
import api from '../../../utils/api';
import {formatDate, MealType} from '../constants';
import {MealPlan, MealPlanCreate, MealPlanItem, MealPlanUpdate, Recipe} from '../types';


const createEmptyMealPlan = (weekStart: Date): MealPlanCreate => {
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);

    return {
        name: `Week of ${formatDate(weekStart)}`,
        description: '',
        start_date: formatDate(weekStart),
        end_date: formatDate(weekEnd),
        days: Array.from({length: 7}).map((_, index) => ({
            date: formatDate(new Date(weekStart.getTime() + index * 86400000)),
            items: [],
        })),
    };
};

const toMealPlanUpdate = (plan: MealPlan): MealPlanUpdate => ({
    name: plan.name,
    description: plan.description,
    start_date: plan.start_date,
    end_date: plan.end_date,
    days: plan.days.map(day => ({
        date: day.date,
        notes: day.notes,
        items: day.items.map(item => ({
            recipe_id:
                typeof item.recipe_id === 'string'
                    ? item.recipe_id
                    : (item as any).recipe?.id ?? null,
            meal_type: item.meal_type,
            servings: item.servings,
            notes: item.notes,
        })),
    })),
});

const cloneMealPlan = (plan: MealPlan): MealPlan =>
    JSON.parse(JSON.stringify(plan));

export const useMealPlan = (currentDate: Date) => {
    const weekStart = useMemo(() => {
        const start = new Date(currentDate);
        start.setHours(0, 0, 0, 0);
        start.setDate(start.getDate() - start.getDay());
        return start;
    }, [currentDate]);

    const weekEnd = useMemo(() => {
        const end = new Date(weekStart);
        end.setDate(end.getDate() + 6);
        return end;
    }, [weekStart]);

    const [mealPlan, setMealPlan] = useState<MealPlan | null>(null);
    const [loading, setLoading] = useState(true);

    const enrichWithRecipes = useCallback(async (plan: MealPlan): Promise<MealPlan> => {
        const recipeIds = Array.from(
            new Set(plan.days.flatMap(day => day.items.map(item => item.recipe_id)).filter(Boolean)),
        ) as string[];

        if (!recipeIds.length) return plan;

        const map: Record<string, Recipe> = {};
        await Promise.all(
            recipeIds.map(async id => {
                try {
                    const {data} = await api.get(`/recipes/${id}`, {withCredentials: true});
                    map[id] = data;
                } catch (error) {
                    console.error('Failed to fetch recipe', id, error);
                }
            }),
        );

        plan.days.forEach(day =>
            day.items.forEach(item => {
                if (item.recipe_id && map[item.recipe_id]) item.recipe = map[item.recipe_id];
            }),
        );

        return plan;
    }, []);

    const fetchPlan = useCallback(async () => {
        setLoading(true);
        try {
            const {data} = await api.get(`/meal-plans/`, {
                params: {
                    start_date: formatDate(weekStart),
                    end_date: formatDate(weekEnd),
                    limit: 1,
                },
                withCredentials: true,
            });

            let plan: MealPlan;
            if (data.items.length) {
                plan = data.items[0] as MealPlan;
            } else {
                const {data: created} = await api.post(`/meal-plans/`, createEmptyMealPlan(weekStart), {
                    withCredentials: true,
                });
                plan = created as MealPlan;
            }

            plan = await enrichWithRecipes(plan);
            setMealPlan(plan);
        } catch (error) {
            console.error('Failed to load meal plan', error);
            setMealPlan(null);
        } finally {
            setLoading(false);
        }
    }, [enrichWithRecipes, weekEnd, weekStart]);

    useEffect(() => {
        void fetchPlan();
    }, [fetchPlan]);

    const saveMealPlan = useCallback(async (plan: MealPlan) => {
        await api.put(`/meal-plans/${plan.id}`, toMealPlanUpdate(plan), {
            withCredentials: true,
        });
    }, []);

    const updateMealPlan = useCallback(
        async (updater: (draft: MealPlan) => void) => {
            if (!mealPlan) return;
            const clone = cloneMealPlan(mealPlan);
            updater(clone);
            setMealPlan(clone);
            await saveMealPlan(clone);
        },
        [mealPlan, saveMealPlan],
    );

    const deleteMealPlan = useCallback(async () => {
        if (!mealPlan) return;
        await api.delete(`/meal-plans/${mealPlan.id}`, {withCredentials: true});
        setMealPlan(null);
    }, [mealPlan]);

    const assignRecipeToMeal = useCallback(
        async (dayIndex: number, mealType: MealType, recipe: Recipe) => {
            await updateMealPlan(draft => {
                const day = draft.days[dayIndex];
                const existing = day.items.find(item => item.meal_type === mealType);
                if (existing) {
                    existing.recipe_id = recipe.id;
                    existing.recipe = recipe;
                } else {
                    day.items.push({
                        id: crypto.randomUUID(),
                        day_id: day.id,
                        recipe_id: recipe.id,
                        meal_type: mealType,
                        servings: null,
                        notes: null,
                        recipe,
                    } as MealPlanItem);
                }
            });
        },
        [updateMealPlan],
    );

    const updateMealNotes = useCallback(
        async (dayIndex: number, mealType: MealType, notes: string) => {
            await updateMealPlan(draft => {
                const day = draft.days[dayIndex];
                const existing = day.items.find(item => item.meal_type === mealType);
                if (existing) {
                    existing.notes = notes;
                } else {
                    day.items.push({
                        id: crypto.randomUUID(),
                        day_id: day.id,
                        recipe_id: null,
                        meal_type: mealType,
                        notes,
                        servings: null,
                    } as MealPlanItem);
                }
            });
        },
        [updateMealPlan],
    );

    const removeMeal = useCallback(
        async (dayIndex: number, mealType: MealType) => {
            await updateMealPlan(draft => {
                const day = draft.days[dayIndex];
                day.items = day.items.filter(item => item.meal_type !== mealType);
            });
        },
        [updateMealPlan],
    );

    const importToShoppingList = useCallback(async () => {
        if (!mealPlan) return;
        await api.post(
            `/shoppinglist/import-meal-plan`,
            {},
            {params: {meal_plan_id: mealPlan.id}, withCredentials: true},
        );
    }, [mealPlan]);

    return {
        mealPlan,
        loading,
        weekStart,
        weekEnd,
        refresh: fetchPlan,
        updateMealPlan,
        deleteMealPlan,
        assignRecipeToMeal,
        updateMealNotes,
        removeMeal,
        importToShoppingList,
    };
};
