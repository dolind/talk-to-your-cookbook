import {FC} from 'react';
import {Grid, Typography} from '@mui/material';
import {MealPlan, MealPlanItem} from '../types';
import {MEAL_TYPES, MealType} from '../constants';
import {MealCard} from './MealCard';

interface MealPlanWeekViewProps {
    mealPlan: MealPlan;
    onEditMeal: (dayIndex: number, mealType: MealType) => void;
}

export const MealPlanWeekView: FC<MealPlanWeekViewProps> = ({mealPlan, onEditMeal}) => (
    <Grid container spacing={2}>
        <Grid item xs={12}>
            <Typography variant="h6">Weekly Meal Plan</Typography>
        </Grid>

        <Grid container item spacing={2}>
            <Grid item xs={2}/>
            {mealPlan.days.map(day => (
                <Grid item xs key={day.date}>
                    <Typography variant="subtitle1" align="center">
                        {new Date(day.date).toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric',
                        })}
                    </Typography>
                </Grid>
            ))}
        </Grid>

        {MEAL_TYPES.map(mealType => (
            <Grid container item spacing={2} key={mealType}>
                <Grid item xs={2}>
                    <Typography variant="subtitle2" sx={{textTransform: 'capitalize'}}>
                        {mealType}
                    </Typography>
                </Grid>
                {mealPlan.days.map((day, dayIndex) => {
                    const item: MealPlanItem | undefined = day.items.find(
                        candidate => candidate.meal_type === mealType,
                    );
                    return (
                        <Grid item xs key={`${day.date}-${mealType}`}>
                            <MealCard
                                item={item}
                                mealType={mealType}
                                onEdit={() => onEditMeal(dayIndex, mealType)}
                            />
                        </Grid>
                    );
                })}
            </Grid>
        ))}
    </Grid>
);
