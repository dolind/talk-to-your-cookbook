import {useState} from 'react';
import api from '../../../../utils/api';
import {RecipeFormState, RecipeRead, RecipeTextUpdater, RecipeUpdate, RecipeValueUpdater} from '../types';

const emptyForm: RecipeUpdate = {
    title: '',
    description: '',
    prep_time: 0,
    cook_time: 0,
    categories: [],
    tags: [],
    source: '',
    rating: null,
    ingredients: [],
    instructions: [],
    nutrition: null,
};

const mapRecipeToForm = (recipe: RecipeRead): RecipeUpdate => ({
    title: recipe.title,
    description: recipe.description ??'',
    prep_time: recipe.prep_time,
    cook_time: recipe.cook_time,
    categories: recipe.categories,
    tags: recipe.tags,
    source: recipe.source ?? '',
    rating: recipe.rating ?? null,
    ingredients: recipe.ingredients.map(ingredient => ({name: ingredient.name})),
    instructions: recipe.instructions.map(instruction => ({
        step: instruction.step,
        instruction: instruction.instruction,
    })),
    nutrition: recipe.nutrition,
});

const toTextFields = (recipe?: RecipeRead) => ({
    ingredients:
        (recipe?.ingredients ?? [])
            .map(ingredient => [ingredient.quantity, ingredient.unit, ingredient.name].filter(Boolean).join(' ').trim())
            .join('\n'),
    instructions: (recipe?.instructions ?? [])
        .map(instruction => instruction.instruction)
        .join('\n\n'),
    categories: (recipe?.categories ?? []).join('\n'),
});

const parseTextFields = (state: RecipeFormState): RecipeUpdate => ({
    ...state.values,
    rating: state.values.rating == null ? null : Number(state.values.rating),
    ingredients: (state.text.ingredients ?? '')
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean)
        .map(line => {
            const parts = line.split(/\s+/);
            if (parts.length === 1) return {name: parts[0]};
            if (parts.length === 2) return {quantity: parts[0], name: parts[1]};
            const [quantity, unit, ...nameParts] = parts;
            return {quantity, unit, name: nameParts.join(' ')};
        }),
    instructions: (state.text.instructions ?? '')
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean)
        .map((instruction, index) => ({step: index + 1, instruction})),
    categories: (state.text.categories ?? '')
        .split('\n')
        .map(category => category.trim())
        .filter(Boolean),
});

export const useRecipeForm = (initialData?: RecipeRead) => {
    const [state, setState] = useState<RecipeFormState>({
        values: initialData ? mapRecipeToForm(initialData) : emptyForm,
        text: toTextFields(initialData),
        newImage: null,
        removeImage: false,
    });

    const isNew = !initialData;

    const updateValue: RecipeValueUpdater = (key, value) => {
        setState(prev => ({...prev, values: {...prev.values, [key]: value}}));
    };

    const updateText: RecipeTextUpdater = (key, value) => {
        setState(prev => ({...prev, text: {...prev.text, [key]: value}}));
    };

    const setNewImage = (file: File | null) => {
        setState(prev => ({...prev, newImage: file, removeImage: file ? false : prev.removeImage}));
    };

    const setRemoveImage = (remove: boolean) => {
        setState(prev => ({...prev, removeImage: remove, newImage: remove ? null : prev.newImage}));
    };

    const saveRecipe = async (): Promise<RecipeRead> => {
        const payload = parseTextFields(state);
        const formData = new FormData();
        formData.append('data', JSON.stringify(payload));

        if (state.newImage) formData.append('file', state.newImage);
        if (state.removeImage) formData.append('delete_image', 'true');

        const endpoint = `/recipes`;
        const response = isNew
            ? await api.post<RecipeRead>(endpoint, formData, {
                withCredentials: true,
                headers: {'Content-Type': 'multipart/form-data'},
            })
            : await api.put<RecipeRead>(`${endpoint}/${initialData!.id}`, formData, {
                withCredentials: true,
                headers: {'Content-Type': 'multipart/form-data'},
            });

        return response.data;
    };

    return {
        state,
        isNew,
        updateValue,
        updateText,
        setNewImage,
        setRemoveImage,
        saveRecipe,
    };
};
