import {FC, useEffect, useRef} from 'react';
import {Avatar, Box, Card, Divider, Paper, Typography} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PersonIcon from '@mui/icons-material/Person';
import {grey} from '@mui/material/colors';
import ReactMarkdown from 'react-markdown';
import {ChatMessage} from '../types';
import {Link} from "react-router-dom";
import remarkGfm from "remark-gfm";

interface ChatMessagesPanelProps {
    messages: ChatMessage[];
    loading: boolean;
}

export const ChatMessagesPanel: FC<ChatMessagesPanelProps> = ({messages, loading}) => {
    const messagesEndRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({behavior: 'smooth'});
    }, [messages]);

    const autolinkToMarkdown = (text) =>
        text.replace(
            /^(\s*\d+\. )([^(\n]+)\s*\(<(https?:\/\/[^>]+)>\)/gm,
            (match, prefix, title, url) =>
                `${prefix}[${title.trim()}](${url})`
        );
    return (
        <Card
            sx={{
                flexGrow: 1,
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                bgcolor: 'background.paper',
                borderRadius: 2,
                overflow: 'hidden',
            }}
        >
            <Box
                sx={{
                    flexGrow: 1,
                    overflowY: 'auto',
                    px: 3,
                    py: 2,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 2,
                }}
            >
                {messages.map(message => {
                    const isAssistant = message.sender === 'assistant';

                    return (
                        <Box
                            key={message.id}
                            sx={{
                                display: 'flex',
                                flexDirection: 'row',
                                alignItems: 'flex-start',
                                alignSelf: isAssistant ? 'flex-start' : 'flex-end',
                                maxWidth: '100%',
                            }}
                        >
                            {isAssistant && (
                                <Avatar sx={{bgcolor: 'primary.main', mr: 1}}>
                                    <SmartToyIcon/>
                                </Avatar>
                            )}

                            <Paper
                                elevation={0}
                                sx={{
                                    p: 2,
                                    borderRadius: 2,
                                    bgcolor: isAssistant ? 'background.default' : 'primary.main',
                                    color: isAssistant ? 'text.primary' : '#fff',
                                    maxWidth: '100%',
                                    wordBreak: 'break-word',
                                }}
                            >


                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}

                                    children={autolinkToMarkdown(
                                        message.content.replace(/\r\n/g, "\n")
                                    )}

                                    components={{
                                        a: ({href, children, ...props}) => {

                                            if (href && href.startsWith("http://recipe?")) {
                                                console.log(href);
                                                const recipeId = href.replace("http://recipe?", "");
                                                console.log(recipeId);
                                                return (
                                                    <Link
                                                        to={`/recipes/${recipeId}`}
                                                        style={{color: "#1976d2", textDecoration: "underline"}}
                                                    >
                                                        {children}
                                                    </Link>
                                                );
                                            }

                                            return (
                                                <a href={href} {...props} target="_blank" rel="noopener noreferrer">
                                                    {children}
                                                </a>
                                            );
                                        },

                                        // text: ({node, ...props}) => (
                                        //     <span style={{whiteSpace: "pre-wrap"}}>{props.children}</span>
                                        // ),

                                        // p: ({node, ...props}) => (
                                        //     <Typography
                                        //         variant="body1"
                                        //         component="p"
                                        //         sx={{whiteSpace: "pre-wrap", mb: 1}}
                                        //         {...props}
                                        //     />
                                        // ),
                                    }}
                                />

                            </Paper>

                            {!isAssistant && (
                                <Avatar sx={{bgcolor: grey[500], ml: 1}}>
                                    <PersonIcon/>
                                </Avatar>
                            )}
                        </Box>
                    );
                })}

                {loading && (
                    <Box sx={{display: 'flex', alignItems: 'center', mt: 1}}>
                        <Avatar sx={{bgcolor: 'primary.main', mr: 1}}>
                            <SmartToyIcon/>
                        </Avatar>
                        <Typography variant="body2" sx={{fontStyle: 'italic', color: 'text.secondary'}}>
                            Typing…
                        </Typography>
                    </Box>
                )}

                <div ref={messagesEndRef}/>
            </Box>

            <Divider/>
        </Card>
    );
};
