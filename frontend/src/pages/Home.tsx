import {useNavigate} from 'react-router-dom';
import {Box, Button, Card, CardActionArea, CardContent, Grid, Typography} from '@mui/material';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import ChatIcon from '@mui/icons-material/Chat';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import UploadIcon from '@mui/icons-material/Upload';
import {ShoppingBag} from "@mui/icons-material";

const Home = () => {
    const navigate = useNavigate();

    const features = [
        {
            title: 'AI Chat Assistant',
            description: 'Ask questions about your own recipe data using retrieval-augmented generation.',
            icon: <ChatIcon fontSize="large" color="primary"/>,
            path: '/chat'
        },
        {
            title: 'Recipe Scanner',
            description: 'Ingest scanned cookbook pages and create structured recipe data using AI pipelines.',
            icon: <UploadIcon fontSize="large" color="primary"/>,
            path: '/ocr'
        },
        {
            title: 'Recipe Collection',
            description: 'View and explore OCR-extracted recipes stored in structured form.',
            icon: <RestaurantIcon fontSize="large" color="primary"/>,
            path: '/recipes'
        },
        {
            title: 'Meal Planning',
            description: 'Example workflow to contextualize how AI could support planning features.',
            icon: <CalendarMonthIcon fontSize="large" color="primary"/>,
            path: '/meal-plans'
        },
        {
            title: 'Shopping List',
            description: 'Static demonstration of a traditional supporting workflow.',
            icon: <ShoppingBag fontSize="large" color="primary"/>,
            path: '/shoppinglist'
        }
    ];

    return (
        <Box sx={{mt: {xs: 2, md: 4}}}>
            <Box sx={{
                textAlign: 'center',
                mb: 6,
                p: 4,
                borderRadius: 4,
                bgcolor: 'background.paper',
                boxShadow: '0 4px 20px rgba(0,0,0,0.05)'
            }}>
                <Typography variant="h3" component="h1" gutterBottom>
                    AI-Augmented Recipe Workspace
                </Typography>
                <Typography variant="h6" color="text.secondary" sx={{mb: 3, maxWidth: 800, mx: 'auto'}}>
                    Explore how AI workflows integrate into a familiar recipe management interface.
                    Upload cookbook pages, extract structured recipes, and ask questions about your own recipes.
                </Typography>
                <Button
                    variant="contained"
                    size="large"
                    onClick={() => navigate('/chat')}
                    startIcon={<ChatIcon/>}
                    sx={{mt: 2}}
                >
                    Start Talking to your own Recipes!
                </Button>
            </Box>

            <Typography variant="h4" component="h2" sx={{mb: 3, mt: 6}}>
                Demonstration Areas
            </Typography>

            <Grid container spacing={3}>
                {features.map((feature) => (
                    <Grid item xs={12} sm={6} md={3} key={feature.title}>
                        <Card sx={{height: '100%', display: 'flex', flexDirection: 'column'}}>
                            <CardActionArea
                                sx={{flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'flex-start'}}
                                onClick={() => navigate(feature.path)}
                            >
                                <CardContent>
                                    <Box sx={{display: 'flex', justifyContent: 'center', width: '100%', mb: 2}}>
                                        {feature.icon}
                                    </Box>
                                    <Typography gutterBottom variant="h6" component="div">
                                        {feature.title}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        {feature.description}
                                    </Typography>
                                </CardContent>
                            </CardActionArea>
                        </Card>
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
};

export default Home;
