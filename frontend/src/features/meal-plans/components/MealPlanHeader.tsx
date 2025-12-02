import {FC} from 'react';
import {Box, Button, IconButton, Typography} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import TodayIcon from '@mui/icons-material/Today';

interface MealPlanHeaderProps {
    weekRangeLabel: string;
    onPrevWeek: () => void;
    onNextWeek: () => void;
    viewMode: 'day' | 'week';
    onToggleView: () => void;
}

export const MealPlanHeader: FC<MealPlanHeaderProps> = ({
                                                            weekRangeLabel,
                                                            onPrevWeek,
                                                            onNextWeek,
                                                            viewMode,
                                                            onToggleView,
                                                        }) => (
    <Box sx={{display: 'flex', alignItems: 'center', mb: 3, justifyContent: 'space-between'}}>
        <Box sx={{display: 'flex', alignItems: 'center'}}>
            <IconButton onClick={onPrevWeek}>
                <ArrowBackIcon/>
            </IconButton>
            <Typography variant="h6" sx={{mx: 2, display: 'flex', alignItems: 'center'}}>
                <TodayIcon sx={{mr: 1}}/>
                {weekRangeLabel}
            </Typography>
            <IconButton onClick={onNextWeek}>
                <ArrowForwardIcon/>
            </IconButton>
        </Box>

        <Button variant="outlined" onClick={onToggleView}>
            {viewMode === 'day' ? 'Week View' : 'Day View'}
        </Button>
    </Box>
);
