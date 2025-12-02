import {useAuth} from '../context/AuthContext';
import {useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {Box, Button, Paper, Stack, TextField, Typography,} from '@mui/material';

type FormData = {
    email: string;
    password: string;
    first_name?: string;
    last_name?: string;
    is_active: boolean | null;
};

type AuthFormProps = {
    mode?: 'login' | 'register';
};

const AuthForm = ({mode = 'login'}: AuthFormProps) => {
    const {login, register} = useAuth();
    const navigate = useNavigate();
    const [isLogin, setIsLogin] = useState(mode === 'login');

    const [form, setForm] = useState<FormData>({
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        is_active: true,
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        console.log('Form submitted:', form);
        try {
            if (isLogin) {
                console.log('Attempting login...');
                await login(form.email, form.password);
                console.log('Login success');
            } else {
                console.log('Attempting register...');
                await register(form);
                await login(form.email, form.password);
                console.log('Register success');
            }
            navigate('/recipes');
        } catch (error) {
            alert('Authentication failed. Please try again.');
        }
    };

    return (
        <Box
            component={Paper}
            elevation={3}
            sx={{maxWidth: 400, mx: 'auto', mt: 8, p: 4}}
        >
            <Typography variant="h5" mb={3} align="center">
                {isLogin ? 'Login to Your Account' : 'Create a New Account'}
            </Typography>
            <form onSubmit={handleSubmit}>
                <Stack spacing={2}>
                    {!isLogin && (
                        <>
                            <TextField
                                label="First Name"
                                value={form.first_name}
                                onChange={(e) =>
                                    setForm({...form, first_name: e.target.value})
                                }
                                fullWidth
                            />
                            <TextField
                                label="Last Name"
                                value={form.last_name}
                                onChange={(e) =>
                                    setForm({...form, last_name: e.target.value})
                                }
                                fullWidth
                            />
                        </>
                    )}
                    <TextField
                        label="Email"
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm({...form, email: e.target.value})}
                        fullWidth
                    />
                    <TextField
                        label="Password"
                        type="password"
                        onChange={(e) => setForm({...form, password: e.target.value})}
                        fullWidth
                    />
                    <Button variant="contained" type="submit" fullWidth>
                        {isLogin ? 'Login' : 'Register'}
                    </Button>
                    <Button
                        variant="text"
                        onClick={() => setIsLogin(!isLogin)}
                        fullWidth
                    >
                        {isLogin ? 'Switch to Register' : 'Switch to Login'}
                    </Button>
                </Stack>
            </form>
        </Box>
    );
};

export default AuthForm;
