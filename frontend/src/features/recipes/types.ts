import {components} from '../../types/api';

export type RecipeRead = components['schemas']['RecipeRead'];
export type RecipePage = components['schemas']['RecipePage'];
export type RecipeFilterOptions = components['schemas']['RecipeFilterOptions'];
export type RecipeDeleteRequest = components['schemas']['RecipeDeleteRequest'];

export type SortOrder = 'recent' | 'name' | 'rating';

export interface RecipeFilters {
    search: string;
    categories: string[];
    tags: string[];
    source: string;
    maxTime: number | '';
    sort: SortOrder;
}

export const INITIAL_FILTERS: RecipeFilters = {
    search: '',
    categories: [],
    tags: [],
    source: '',
    maxTime: '',
    sort: 'recent',
};
