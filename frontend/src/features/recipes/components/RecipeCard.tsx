import AccessTimeIcon from '@mui/icons-material/AccessTime';
import {Box, Card, CardActionArea, CardContent, CardMedia, Checkbox, Chip, Rating, Typography} from '@mui/material';
import {Link} from 'react-router-dom';
import type {RecipeRead} from '../types';

export type RecipeViewMode = 'grid' | 'list';

interface RecipeCardProps {
    recipe: RecipeRead;
    viewMode: RecipeViewMode;
    deleteMode: boolean;
    selected: boolean;
    onToggleSelection: (id: string) => void;
    onStartSelection: (id: string) => void;
    onHoverSelection: (id: string) => void;
}

const BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL;

const RecipeCard = ({
                        recipe,
                        viewMode,
                        deleteMode,
                        selected,
                        onToggleSelection,
                        onStartSelection,
                        onHoverSelection,
                    }: RecipeCardProps) => {
    const handleMouseDown = () => {
        if (!deleteMode) {
            return;
        }

        onStartSelection(recipe.id);
    };

    const handleMouseEnter = () => {
        if (!deleteMode) {
            return;
        }

        onHoverSelection(recipe.id);
    };

    const cardContent = (
        <>
            {viewMode === 'grid' && (
                <CardMedia
                    component="img"
                    height="160"
                    image={`${BASE_URL}/recipe_thumbs/${recipe.image_url ?? ''}`}
                    alt={recipe.title}
                />
            )}
            <CardContent sx={{flexGrow: 1, py: viewMode === 'grid' ? 2 : 1, px: viewMode === 'grid' ? 2 : 1}}>
                <Typography gutterBottom variant={viewMode === 'grid' ? 'h6' : 'subtitle1'}>
                    {recipe.title}
                </Typography>
                <Rating
                    name="read-only-rating"
                    value={recipe.rating ?? 0}
                    precision={0.5}
                    readOnly
                    size="small"
                />
                {viewMode === 'grid' && (
                    <Typography variant="body2" color="text.secondary" sx={{mb: 2}}>
                        {recipe.description}
                    </Typography>
                )}
                <Box sx={{display: 'flex', alignItems: 'center', mb: 1}}>
                    <AccessTimeIcon fontSize="small" color="action" sx={{mr: 1}}/>
                    <Typography variant="body2" color="text.secondary">
                        {(recipe.prep_time ?? 0) + (recipe.cook_time ?? 0)} min
                    </Typography>
                </Box>
                <Box sx={{display: 'flex', flexWrap: 'wrap', gap: 0.5}}>
                    {(recipe.categories ?? []).map(category => (
                        <Chip
                            key={category}
                            label={category}
                            size="small"
                            color="primary"
                            variant="outlined"
                        />
                    ))}
                </Box>
            </CardContent>
        </>
    );

    return (
        <Card
            sx={{
                height: '100%',
                display: viewMode === 'grid' ? 'block' : 'flex',
                position: 'relative',
                border: deleteMode && selected ? '2px solid red' : 'none',
                p: viewMode === 'grid' ? 0 : 1,
                alignItems: 'center',
                borderRadius: 1,
                boxShadow: viewMode === 'grid' ? 1 : 0,
            }}
        >
            {deleteMode && (
                <Checkbox
                    checked={selected}
                    onChange={() => onToggleSelection(recipe.id)}
                    sx={{
                        position: 'absolute',
                        top: 8,
                        left: 8,
                        zIndex: 2,
                        backgroundColor: 'white',
                    }}
                />
            )}

            <Box
                sx={{
                    flexGrow: 1,
                    display: 'flex',
                    flexDirection: viewMode === 'grid' ? 'column' : 'row',
                    cursor: deleteMode ? 'pointer' : 'default',
                }}
                onMouseDown={handleMouseDown}
                onMouseEnter={handleMouseEnter}
            >
                {!deleteMode ? (
                    <CardActionArea
                        component={Link}
                        to={`/recipes/${recipe.id}`}
                        sx={{
                            flexGrow: 1,
                            display: 'flex',
                            flexDirection: viewMode === 'grid' ? 'column' : 'row',
                            alignItems: 'stretch',
                        }}
                    >
                        {cardContent}
                    </CardActionArea>
                ) : (
                    cardContent
                )}
            </Box>
        </Card>
    );
};

export default RecipeCard;
