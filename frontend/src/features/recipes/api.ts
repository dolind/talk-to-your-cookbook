import api from '../../utils/api';
import {RecipeDeleteRequest} from './types';

export const deleteRecipes = async (ids: string[]) => {
    if (ids.length === 0) {
        return;
    }

    const payload: RecipeDeleteRequest = {ids};

    await api.delete('/recipes/bulk-delete', {
        data: payload,
        withCredentials: true,
    });
};
