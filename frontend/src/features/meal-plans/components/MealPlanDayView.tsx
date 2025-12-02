import {FC} from 'react';
import {Box, Grid, Tab, Tabs} from '@mui/material';
import {MealPlan, MealPlanItem} from '../types';
import {MEAL_TYPES, MealType} from '../constants';
import {MealCard} from './MealCard';

interface MealPlanDayViewProps {
    mealPlan: MealPlan;
    activeDayIndex: number;
    onDayChange: (index: number) => void;
    onEditMeal: (dayIndex: number, mealType: MealType) => void;
}

export const MealPlanDayView: FC<MealPlanDayViewProps> = ({
                                                              mealPlan,
                                                              activeDayIndex,
                                                              onDayChange,
                                                              onEditMeal,
                                                          }) => (
    <>
        <Box sx={{borderBottom: 1, borderColor: 'divider'}}>
            <Tabs
                value={activeDayIndex}
                onChange={(_, value) => onDayChange(value)}
                variant="scrollable"
                scrollButtons="auto"
            >
                {mealPlan.days.map((day) => (
                    <Tab
                        key={day.date}
                        label={new Date(day.date).toLocaleDateString('en-US', {
                            weekday: 'short',
                            month: 'short',
                            day: 'numeric',
                        })}
                    />
                ))}
            </Tabs>
        </Box>

        {activeDayIndex < mealPlan.days.length && (
            <Box sx={{pt: 3}}>
                <Grid container spacing={3}>
                    {MEAL_TYPES.map(mealType => {
                        const item: MealPlanItem | undefined = mealPlan.days[activeDayIndex].items.find(
                            candidate => candidate.meal_type === mealType,
                        );
                        return (
                            <Grid item xs={12} md={4} key={mealType}>
                                <MealCard
                                    item={item}
                                    mealType={mealType}
                                    onEdit={() => onEditMeal(activeDayIndex, mealType)}
                                />
                            </Grid>
                        );
                    })}
                </Grid>
            </Box>
        )}
    </>
);
