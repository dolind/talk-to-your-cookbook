import {FC} from 'react';
import {Box, Card, CardContent, Chip, IconButton, Typography} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import {MealPlanItem} from '../types';
import {MealType, MEDIA_BASE_URL} from '../constants';

interface MealCardProps {
    item: MealPlanItem | undefined;
    mealType: MealType;
    onEdit: () => void;
}

export const MealCard: FC<MealCardProps> = ({item, mealType, onEdit}) => (
    <Card variant="outlined" sx={{height: '100%', position: 'relative'}}>
        {item?.recipe ? (
            <>
                <Box
                    sx={{
                        position: 'relative',
                        paddingTop: '56.25%',
                        backgroundImage: `url(${MEDIA_BASE_URL}/recipe_thumbs/${item?.recipe.image_url})`,
                        backgroundSize: 'cover',
                        backgroundPosition: 'center',
                    }}
                />
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        {item.recipe.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                        {item.recipe.description}
                    </Typography>
                    <Typography variant="body2">
                        {(item?.recipe?.prep_time ?? 0) + (item?.recipe?.cook_time ?? 0)} min
                    </Typography>
                </CardContent>
            </>
        ) : item?.notes ? (
            <CardContent sx={{height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                <Typography variant="body2" color="text.secondary" align="center">
                    {item.notes}
                </Typography>
            </CardContent>
        ) : (
            <Box sx={{height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
                <Typography variant="body2" color="text.secondary">
                    No {mealType}
                </Typography>
            </Box>
        )}

        <Chip
            label={mealType}
            color="primary"
            size="small"
            sx={{position: 'absolute', top: 8, left: 8, textTransform: 'capitalize'}}
        />

        <IconButton
            size="small"
            sx={{position: 'absolute', top: 8, right: 8, backgroundColor: 'grey'}}
            onClick={onEdit}
        >
            {item ? <EditIcon fontSize="small"/> : <AddIcon fontSize="small"/>}
        </IconButton>
    </Card>
);
