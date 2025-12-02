import {useAuth} from '../context/AuthContext';
import api from "../utils/api";
import {userPreferences} from "../hooks/userPreferences";
import {useEffect, useMemo, useState} from "react";
import {downloadBlob} from "../utils/download";
import {Box, Button, Card, CardContent, Divider, Paper, Stack, TextField, Typography,} from "@mui/material";
import {Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis} from 'recharts';

const Profile = () => {
    const {user, updateUser, logout} = useAuth();
    const {prefs} = userPreferences();

    const [firstName, setFirstName] = useState('');
    const [lastName, setLastName] = useState('');
    const [stats, setStats] = useState(null);

    const [prefsForm, setPrefsForm] = useState({
        dietary_preferences: "",
        allergens: "",
        nutrition_targets: ""
    });

    useEffect(() => {
        if (user) {
            setFirstName(user.first_name ?? '');
            setLastName(user.last_name ?? '');
        }

        api.get("/users/me/stats", {withCredentials: true})
            .then(res => setStats(res.data))
            .catch(err => console.error("Failed to load stats", err));


    }, [user]);

    const chartData = useMemo(() => {
        if (!stats?.dates) return [];

        return Object.entries(stats.dates)
            .map(([date, count]) => ({
                date: new Date(date).toLocaleDateString(),
                count
            }))
            .sort((a, b) => new Date(a.date) - new Date(b.date));
    }, [stats]);
    useEffect(() => {
        api.get("/users/me/preferences", {withCredentials: true})
            .then(res => {
                const p = res.data;

                setPrefsForm({
                    dietary_preferences:
                        p.dietary_preferences == null
                            ? ""
                            : JSON.stringify(p.dietary_preferences, null, 2),

                    allergens:
                        p.allergens == null
                            ? ""
                            : JSON.stringify(p.allergens, null, 2),

                    nutrition_targets:
                        p.nutrition_targets == null
                            ? ""
                            : JSON.stringify(p.nutrition_targets, null, 2),
                });
            })
            .catch(err => console.error("Failed to load prefs", err));
    }, []);

    if (!user) return <p>Loading...</p>;

    async function exportPaprika() {
        const blob = await api.get("/recipes/export/paprika", {responseType: "blob"});
        downloadBlob(blob, "recipes.paprikarecipes");
    }

    async function exportMealie() {
        const blob = await api.get("/recipes/export/mealie", {responseType: "blob"});
        downloadBlob(blob, "mealie.json");
    }

    async function handleImport(e) {
        const file = e.target.files[0];
        const form = new FormData();
        form.append("file", file);

        await api.post("/recipes/import", form, {
            headers: {'Content-Type': undefined}
        });
        alert("Import completed");
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        await updateUser({first_name: firstName, last_name: lastName});
    };

    async function handlePrefsSave(e) {
        e.preventDefault();

        const payload = {
            dietary_preferences: prefsForm.dietary_preferences ? JSON.parse(prefsForm.dietary_preferences) : null,
            allergens: prefsForm.allergens ? JSON.parse(prefsForm.allergens) : null,
            nutrition_targets: prefsForm.nutrition_targets ? JSON.parse(prefsForm.nutrition_targets) : null
        };

        await api.put("/users/me/preferences", payload, {withCredentials: true});
    }

    async function handleDeleteAll() {
        if (!window.confirm("Delete ALL recipes? This cannot be undone!")) return;

        try {
            await api.delete("/recipes/recipes", {withCredentials: true});
            alert("All recipes deleted!");
            window.location.reload();
        } catch (err) {
            console.error("Failed to delete recipes", err);
            alert("Failed to delete all recipes");
        }
    }

    return (
        <Box sx={{maxWidth: 900, mx: 'auto', mt: 6, p: 2}}>
            <Paper sx={{p: 4}} elevation={3}>
                <Typography variant="h4" gutterBottom>
                    Profile
                </Typography>
                <Typography variant="subtitle1" color="text.secondary" sx={{mb: 2}}>
                    {user.email}
                </Typography>

                <Button variant="contained" color="error" onClick={logout}>
                    Logout
                </Button>

                <Divider sx={{my: 4}}/>

                {/* Account Info */}
                <Typography variant="h6" gutterBottom>Account Info</Typography>
                <form onSubmit={handleSubmit}>
                    <Stack spacing={2} direction="row" sx={{mb: 2}}>
                        <TextField
                            label="First Name"
                            fullWidth
                            value={firstName}
                            onChange={(e) => setFirstName(e.target.value)}
                        />
                        <TextField
                            label="Last Name"
                            fullWidth
                            value={lastName}
                            onChange={(e) => setLastName(e.target.value)}
                        />
                    </Stack>

                    <Button variant="contained" type="submit">
                        Save Name
                    </Button>
                </form>

                <Divider sx={{my: 4}}/>

                {/* Import/Export */}
                <Typography variant="h6" gutterBottom>Import / Export Recipes</Typography>

                <Stack direction="row" spacing={2} sx={{mb: 2}}>
                    <Button variant="contained" onClick={exportPaprika}>
                        Export Paprika
                    </Button>
                    <Button variant="contained" onClick={exportMealie}>
                        Export Mealie
                    </Button>
                </Stack>

                <Button variant="outlined" component="label">
                    Import Data
                    <input
                        hidden
                        type="file"
                        accept=".paprikarecipes,application/json"
                        onChange={handleImport}
                    />
                </Button>

                <Divider sx={{my: 4}}/>
                <Button
                    variant="contained"
                    color="error"
                    sx={{mt: 2}}
                    onClick={handleDeleteAll}
                >
                    Delete All Recipes
                </Button>
                <Divider sx={{my: 4}}/>
                {/* Preferences */}
                <Typography variant="h6" gutterBottom>Preferences</Typography>

                <form onSubmit={handlePrefsSave}>
                    <Stack spacing={2} sx={{mb: 2}}>
                        <TextField
                            label="Dietary Preferences (JSON)"
                            multiline
                            rows={4}
                            fullWidth
                            placeholder={`{
  "diet": "balanced",
  "vegetarian": false,
}`}
                            value={prefsForm.dietary_preferences}
                            onChange={(e) =>
                                setPrefsForm({...prefsForm, dietary_preferences: e.target.value})
                            }
                        />

                        <TextField
                            label="Allergens (JSON)"
                            multiline
                            rows={3}
                            fullWidth
                            placeholder={`["milk", "eggs", "peanuts"]`}
                            value={prefsForm.allergens}
                            onChange={(e) =>
                                setPrefsForm({...prefsForm, allergens: e.target.value})
                            }
                        />

                        <TextField
                            label="Nutrition Targets (JSON)"
                            multiline
                            rows={4}
                            fullWidth
                            placeholder={`{
  "calories": 2200,
  "protein_g": 120,
}`}
                            value={prefsForm.nutrition_targets}
                            onChange={(e) =>
                                setPrefsForm({...prefsForm, nutrition_targets: e.target.value})
                            }
                        />

                    </Stack>

                    <Button variant="contained" type="submit">
                        Save Preferences
                    </Button>
                </form>

                <Divider sx={{my: 4}}/>

                {/* Stats */}
                <Typography variant="h6" gutterBottom>Statistics</Typography>

                {!stats ? (
                    <Typography>Loading stats...</Typography>
                ) : (
                    <Stack spacing={3}>
                        {/* High-level summary */}
                        <Card>
                            <CardContent>
                                <Typography variant="h6">Overview</Typography>
                                <Typography>Total Recipes: {stats.total_recipes}</Typography>
                                <Typography>Images: {stats.images}</Typography>
                                <Typography>
                                    Storage Used: {(stats.storage_bytes / (1024 * 1024)).toFixed(2)} MB
                                </Typography>
                                <Typography variant="body2" color="text.secondary" sx={{mt: 1}}>
                                    Account created: {new Date(stats.user.created_at).toLocaleDateString()}
                                </Typography>
                            </CardContent>
                        </Card>

                        {/* Top Tags */}
                        <Card>
                            <CardContent>
                                <Typography variant="h6" gutterBottom>Top Tags</Typography>
                                {stats.top_tags.length === 0 ? (
                                    <Typography>No tags found.</Typography>
                                ) : (
                                    <Stack spacing={1}>
                                        {stats.top_tags.map(([tag, count]) => (
                                            <Typography key={tag}>
                                                • <strong>{tag}</strong> — {count}
                                            </Typography>
                                        ))}
                                    </Stack>
                                )}
                            </CardContent>
                        </Card>

                        {/* Categories */}
                        <Card>
                            <CardContent>
                                <Typography variant="h6" gutterBottom>Categories</Typography>
                                <Stack spacing={1}>
                                    {Object.entries(stats.categories).map(([cat, count]) => (
                                        <Typography key={cat}>
                                            • <strong>{cat}</strong> — {count}
                                        </Typography>
                                    ))}
                                </Stack>
                            </CardContent>
                        </Card>

                        {/* Creation dates */}
                        <Card>
                            <CardContent>
                                <Typography variant="h6" mb={2}>Recipes Added Over Time</Typography>

                                {/* Chart container with fixed height to avoid -1 width/height errors */}
                                <Box sx={{width: "100%", height: 300}}>
                                    <ResponsiveContainer>
                                        <BarChart data={chartData}>
                                            <CartesianGrid strokeDasharray="3 3"/>
                                            <XAxis
                                                dataKey="date"
                                                tick={{fontSize: 11}}
                                                interval={0}
                                                angle={-40}
                                                textAnchor="end"
                                                height={70}
                                            />
                                            <YAxis/>
                                            <Tooltip/>

                                            <Bar dataKey="count" fill="#1976d2"/>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </Box>
                            </CardContent>
                        </Card>
                    </Stack>
                )}

            </Paper>
        </Box>
    );
};

export default Profile;
