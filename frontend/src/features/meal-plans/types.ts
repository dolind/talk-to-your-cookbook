import {components} from '../../types/api';

export type MealPlanBase = components['schemas']['MealPlanRead'];
type MealPlanItemBase = components['schemas']['MealPlanItemRead'];
export type MealPlanCreate = components['schemas']['MealPlanCreate'];
export type MealPlanUpdate = components['schemas']['MealPlanUpdate'];
export type Recipe = components['schemas']['RecipeRead'];
export type RecipePage = components['schemas']['RecipePage'];

export interface MealPlanItem extends MealPlanItemBase {
    recipe?: Recipe;
}

export interface MealPlan extends Omit<MealPlanBase, 'days'> {
    days: {
        date: string;
        id: string;
        notes?: string;
        items: MealPlanItem[];
    }[];
}
