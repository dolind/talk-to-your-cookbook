import React, {useState} from "react";
import {Box, Button, Card, CardContent, Grid, IconButton, Stack, TextField, Typography,} from "@mui/material";
import {ClassificationRecordRead, Page} from "../../../lib/model";
import {addPageToRecord, approveRecord, removePageFromRecord} from "../api/recordsApi";
import {useSnackbar} from "notistack";
import DeleteIcon from "@mui/icons-material/Delete";
import {useOCRStore} from "../../../store/useOCRStore.ts";


const BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL;

type Props = {
    record: ClassificationRecordRead;
    onRefresh: () => void;
    onDelete: (id: string) => void;
};

/**
 * Displays a grouping approval card — showing all image thumbnails
 * for the pages grouped under this record.
 */
export const GroupingCard: React.FC<Props> = ({record, onRefresh, onDelete}) => {
    const {enqueueSnackbar} = useSnackbar();

    const {pages: allPages} = useOCRStore();
    const [pages, setPages] = useState<Page[]>(record.text_pages ?? []);
    const [newPageInput, setNewPageInput] = useState<string>("");

    const handleApprove = async (e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await approveRecord(record.id, "group", pages ?? []);
            enqueueSnackbar("Grouping approved", {variant: "success"});
            onRefresh();
        } catch {
            enqueueSnackbar("Grouping approval failed", {variant: "error"});
        }
    };


    const handleRemovePage = async (pageId: string) => {
        try {
            await removePageFromRecord(record.id, pageId);
            enqueueSnackbar("Page removed from record", {variant: "info"});
            setPages((prev) => prev.filter((p) => p.id !== pageId));
            onRefresh();
        } catch (err) {
            console.error(err);
            enqueueSnackbar("Failed to remove page", {variant: "error"});
        }
    };

    const handleAddPage = async () => {
        const input = newPageInput.trim();
        if (!input) return;

        // ✅ Interpret input as a page number
        const pageNumber = parseInt(input, 10);
        if (isNaN(pageNumber)) {
            enqueueSnackbar("Please enter a valid page number", {
                variant: "warning",
            });
            return;
        }
        console.log(allPages)
        // ✅ Find the page by number in store (for current book)
        const matchedPage = allPages.find((p) => p.page_number === pageNumber);

        if (!matchedPage) {
            enqueueSnackbar(`Page number ${pageNumber} not found in this book`, {
                variant: "error",
            });
            return;
        }

        // ✅ Prevent duplicates
        if (pages.some((p) => p.id === matchedPage.id)) {
            enqueueSnackbar("Page already in group", {variant: "warning"});
            return;
        }

        try {
            await addPageToRecord(record.id, matchedPage.id);
            enqueueSnackbar(`Page ${pageNumber} added to record`, {
                variant: "success",
            });

            setPages((prev) => [
                ...prev,
                {id: matchedPage.id, page_number: matchedPage.page_number},
            ]);

            setNewPageInput("");
            onRefresh();
        } catch (err) {
            console.error(err);
            enqueueSnackbar("Failed to add page", {variant: "error"});
        }
    };
    return (
        <Card
            sx={{
                border: "1px solid #e0e0e0",
                borderRadius: 2,
                height: "auto",
                minHeight: 320,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                position: "relative",
                p: 1,
            }}
        >
            <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                    Review Grouping
                </Typography>

                <Typography variant="body2" color="text.secondary" sx={{mb: 1}}>
                    The system grouped these image pages together:
                </Typography>

                {/* 🔹 Image thumbnails */}
                <Grid container spacing={1}>
                    {pages.map((page) => (
                        <Grid item xs={4} key={page.id}>
                            <Box
                                sx={{
                                    position: "relative", // ✅ Needed so delete button is positioned correctly
                                    border: "1px solid #ddd",
                                    borderRadius: 1,
                                    overflow: "hidden",
                                    "&:hover .delete-btn": {
                                        opacity: 1, // show delete button on hover
                                    },
                                }}
                            >
                                <img
                                    src={`${BASE_URL}/scanner_images/${page.id}.jpg`}
                                    alt={`Page ${page.page_number}`}
                                    style={{
                                        width: "100%",
                                        height: 100,
                                        objectFit: "cover",
                                        display: "block",
                                    }}
                                />
                                <IconButton
                                    className="delete-btn"
                                    size="small"
                                    color="error"
                                    onClick={() => handleRemovePage(page.id)}
                                    sx={{
                                        position: "absolute",
                                        top: 2,
                                        right: 2,
                                        bgcolor: "white",
                                        opacity: 0,
                                        transition: "opacity 0.2s",
                                        boxShadow: 1,
                                        "&:hover": {bgcolor: "#fff0f0"},
                                    }}
                                >
                                    <DeleteIcon fontSize="small"/>
                                </IconButton>
                            </Box>
                            <Typography
                                variant="caption"
                                display="block"
                                align="center"
                                sx={{mt: 0.5}}
                            >
                                Page {page.page_number}
                            </Typography>
                        </Grid>
                    ))}
                </Grid>

                {/* 🔹 If no images found */}
                {pages.length === 0 && (
                    <Typography variant="caption" color="text.secondary" sx={{fontStyle: "italic"}}>
                        (No image pages associated)
                    </Typography>
                )}
            </CardContent>

            <Stack direction="row" spacing={1} sx={{mt: 1, alignItems: "center"}}>
                <TextField
                    size="small"
                    label="Page#"
                    placeholder="e.g. 12"
                    value={newPageInput}
                    onChange={(e) => setNewPageInput(e.target.value)}
                    sx={{flexGrow: 1}}
                />
                <Button
                    variant="outlined"
                    size="small"
                    color="primary"
                    onClick={handleAddPage}
                    disabled={!newPageInput.trim()}
                >
                    Add
                </Button>
                <Button
                    variant="contained"
                    color="success"
                    size="small"
                    onClick={handleApprove}
                >
                    Approve
                </Button>
                <IconButton
                    size="small"
                    color="error"
                    onClick={(e) => {
                        e.stopPropagation();
                        onDelete(record.id);
                    }}
                >
                    <DeleteIcon fontSize="small"/>
                </IconButton>
            </Stack>

        </Card>
    );
};
