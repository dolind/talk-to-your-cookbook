import {
    Box,
    Button,
    CardMedia,
    Chip,
    Divider,
    List,
    ListItem,
    ListItemText,
    Rating,
    Stack,
    Typography,
} from '@mui/material';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';
import {components} from "../../../types/api";
import api from "../../../utils/api.tsx";


type RecipeRead = components['schemas']['RecipeRead'];

const RecipeViewer = ({
                          recipe,
                          onEdit,
                          onDelete,
                          onAsk
                      }: {
    recipe: RecipeRead;
    onEdit: () => void;
    onDelete: () => void;
    onAsk?: () => void;
}) => {

    const BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL;
    console.log(BASE_URL);
    const handleEmail = () => {
        const body = `
${recipe.title}

Ingredients:
${recipe.ingredients?.map(i => `- ${i.name}`).join('\n') ?? ''}

Instructions:
${recipe.instructions?.map(i => `${i.step}. ${i.instruction}`).join('\n') ?? ''}

Prep Time: ${recipe.prep_time} min
Cook Time: ${recipe.cook_time} min
Source: ${recipe.source}
    `.trim();

        const subject = `Recipe: ${recipe.title}`;
        window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    };

    const handleExport = () => {
        const exportData = JSON.stringify(recipe, null, 2);
        const blob = new Blob([exportData], {type: 'application/json'});
        const url = URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.href = url;
        link.download = `${recipe.title.replace(/\s+/g, '_')}.json`;
        link.click();

        URL.revokeObjectURL(url);
    };

    const handleAddToCart = async () => {
        try {
            await api.post(`/shoppinglist/import-recipe`, null, {
                params: {recipe_id: recipe.id},
                withCredentials: true,
            });
            alert('Recipe added to shopping list!');
        } catch (err) {
            console.error('Failed to add to shopping list', err);
            alert('Failed to add to shopping list');
        }
    };

    const handleAddToMealList = () => {
        alert('TODO: Add to Meal List');
    };

    const handleFavourite = () => {
        alert('TODO: Mark as Favourite');
    };

    return (

        <Box sx={{p: 4, maxWidth: 800, mx: 'auto'}}>

            {onAsk && (
                <Button
                    variant="outlined"
                    onClick={onAsk}
                >
                    Ask a Question
                </Button>
            )}
            <div id="printable">{
                <>
                    <Typography variant="h3" gutterBottom>
                        {recipe.title}
                    </Typography>


                    {recipe.image_url && (
                        <CardMedia
                            component="img"
                            height="300"
                            image={`${BASE_URL}/recipe_thumbs/${recipe.image_url}`}
                            alt={recipe.title}
                            sx={{borderRadius: 2, mb: 2, objectFit: 'cover'}}
                        />
                    )}

                    <Rating value={recipe.rating ?? 0} readOnly precision={0.5} sx={{my: 2}}/>
                    {recipe.description && (
                        <Typography sx={{mb: 2}}>
                            {recipe.description}
                        </Typography>
                    )}

                    <Stack direction="row" spacing={1} flexWrap="wrap" sx={{mb: 2}}>
                        {recipe.categories?.map(cat => (
                            <Chip key={cat} label={cat}/>
                        ))}
                        {recipe.tags?.map(tag => (
                            <Chip key={tag} label={tag} variant="outlined"/>
                        ))}
                    </Stack>
                    <Typography>Prep Time: {recipe.prep_time} min</Typography>
                    <Typography>Cook Time: {recipe.cook_time} min</Typography>
                    <Typography>Source: {recipe.source}</Typography>

                    <Divider sx={{my: 3}}/>


                    <Typography variant="h5">Ingredients</Typography>
                    <List dense>
                        {recipe.ingredients.map((i, idx) => (
                            <ListItem key={idx}>
                                <ListItemText
                                    primary={[i.quantity, i.unit, i.name].filter(Boolean).join(' ')}
                                />
                            </ListItem>
                        ))}
                    </List>

                    <Divider sx={{my: 3}}/>

                    <Typography variant="h5">Instructions</Typography>
                    <List dense>
                        {recipe.instructions.map((inst, idx) => (
                            <ListItem key={idx}>
                                <ListItemText primary={`${inst.step}. ${inst.instruction}`}/>
                            </ListItem>
                        ))}
                    </List>

                    {recipe.nutrition && (
                        <>
                            <Divider sx={{my: 3}}/>
                            <Typography variant="h5">Nutrition</Typography>
                            <List dense>
                                {Object.entries(recipe.nutrition)
                                    .filter(([key, val]) =>
                                        val != null &&
                                        typeof val !== 'object' &&
                                        key !== 'id' &&
                                        key !== 'recipe_id'
                                    )
                                    .map(([key, val]) => (
                                        <ListItem key={key}>
                                            <ListItemText primary={`${key}: ${val}`}/>
                                        </ListItem>
                                    ))}
                            </List>
                        </>
                    )}

                </>
            }</div>
            <Box sx={{mt: 4, display: 'flex', flexWrap: 'wrap', gap: 2}}>


                <Button
                    variant="outlined"
                    startIcon={<ShoppingCartIcon/>}
                    onClick={handleAddToCart}
                >
                    Add to Shopping List
                </Button>
                <Button variant="outlined" onClick={handleAddToMealList}>
                    Add to Meal List
                </Button>
                <Button variant="outlined" onClick={handleFavourite}>
                    Favourite
                </Button>
                <Button variant="outlined" onClick={() => window.print()}>
                    Print
                </Button>
                <Button variant="outlined" onClick={handleEmail}>
                    Email
                </Button>
                <Button variant="outlined" onClick={handleExport}>
                    Export JSON
                </Button>

                <Button variant="contained" onClick={onEdit}>Edit</Button>
                <Button variant="outlined" color="error" onClick={onDelete}>Delete</Button>

            </Box>
        </Box>
    );
};

export default RecipeViewer;
