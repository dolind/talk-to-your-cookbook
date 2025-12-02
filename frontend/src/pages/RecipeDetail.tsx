import {useMatch, useNavigate, useParams} from 'react-router-dom';
import {useEffect, useState} from 'react';
import {CircularProgress} from '@mui/material';
import RecipeForm from '../features/recipes/form/RecipeForm';
import RecipeViewer from '../features/recipes/viewer/RecipeViewer';
import api from '../utils/api';
import {components} from '../types/api';
import {deleteRecipes} from "../features/recipes/api.ts";

type RecipeRead = components['schemas']['RecipeRead'];

const RecipeDetail = () => {
    const {id} = useParams();
    const isNew = !!useMatch('/recipes/new');
    const [recipe, setRecipe] = useState<RecipeRead | null>(null);
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(isNew);
    const navigate = useNavigate();

    const handleDelete = async () => {
        if (!recipe) return;

        const confirmed = window.confirm(`Delete recipe "${recipe.title}"?`);
        if (!confirmed) return;

        try {
            await deleteRecipes([recipe.id]); // Reuse bulk delete
            navigate('/recipes');
        } catch (err) {
            console.error('Failed to delete recipe', err);
            alert('Failed to delete recipe.');
        }
    };


    useEffect(() => {
        if (!isNew && id) {
            api
                .get<RecipeRead>(`/recipes/${id}`, {
                    withCredentials: true,
                })
                .then((res) => {
                    setRecipe(res.data);
                })
                .catch((err) => {
                    console.error('Failed to load recipe', err);
                })
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, [id, isNew]);

    if (loading) return <CircularProgress/>;
    if (!recipe && !isNew) return <p>Recipe not found.</p>;

    return isEditing || isNew ? (
        <RecipeForm
            initialData={recipe ?? undefined}
            onSuccess={(updated) => {
                setRecipe(updated);
                setIsEditing(false);
                navigate(`/recipes/${updated.id}`);
            }}
            onCancel={() => {
                if (isNew) {
                    navigate('/recipes');
                } else {
                    setIsEditing(false);
                }
            }}

        />
    ) : (
        <RecipeViewer
            recipe={recipe!}
            onEdit={() => setIsEditing(true)}
            onDelete={handleDelete}
            onAsk={() => navigate(`/chat?recipeId=${recipe!.id}&askRecipeQuestion=1`)}
        />

    );
};

export default RecipeDetail;
