import {useState} from 'react';
import {Outlet} from 'react-router-dom';
import {Box, Container} from '@mui/material';
import Navbar from './Navbar';
import Sidebar from './Sidebar';

const Layout = () => {
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const toggleSidebar = () => {
        setSidebarOpen(!sidebarOpen);
    };

    return (
        <Box sx={{display: 'flex', minHeight: '100vh'}}>
            <Navbar toggleSidebar={toggleSidebar}/>
            <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)}/>
            <Box
                component="main"
                sx={{
                    flexGrow: 1,
                    pt: {xs: 2, sm: 4},
                    pb: 4,
                    px: {xs: 2, sm: 4},
                    mt: '64px',
                }}
            >
                <Container maxWidth="lg">
                    <Outlet/>
                </Container>
            </Box>
        </Box>
    );
};

export default Layout;
