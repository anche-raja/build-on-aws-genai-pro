import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  Avatar,
  Chip,
  CircularProgress,
  Divider,
  Button,
} from '@mui/material';
import {
  Send as SendIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  SmartToy as BotIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { post } from 'aws-amplify/api';
import FeedbackDialog from '../components/FeedbackDialog';

export default function Chat({ user }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [feedbackDialog, setFeedbackDialog] = useState({ open: false, message: null });
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const restOperation = post({
        apiName: 'GenAIAPI',
        path: '/query',
        options: {
          body: {
            query: input,
            user_id: user?.signInDetails?.loginId || 'anonymous',
            conversation_id: conversationId,
          },
        },
      });

      const { body } = await restOperation.response;
      const data = await body.json();

      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        request_id: data.request_id,
        quality_scores: data.quality_scores,
        latency: data.latency,
        cost: data.cost,
        sources: data.sources,
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'error',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFeedback = async (message, feedbackType) => {
    if (!message.request_id) return;

    try {
      await post({
        apiName: 'GenAIAPI',
        path: '/feedback',
        options: {
          body: {
            request_id: message.request_id,
            user_id: user?.signInDetails?.loginId || 'anonymous',
            feedback_type: feedbackType,
          },
        },
      });

      // Update message to show feedback was given
      setMessages(prev =>
        prev.map(msg =>
          msg.request_id === message.request_id
            ? { ...msg, userFeedback: feedbackType }
            : msg
        )
      );
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  const openFeedbackDialog = (message) => {
    setFeedbackDialog({ open: true, message });
  };

  return (
    <Box sx={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      {/* Chat Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h5" gutterBottom>
          AI Knowledge Assistant
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Ask me anything about your documents
        </Typography>
      </Paper>

      {/* Messages Container */}
      <Paper sx={{ flexGrow: 1, overflow: 'auto', p: 2, mb: 2 }}>
        {messages.length === 0 ? (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'text.secondary',
            }}
          >
            <BotIcon sx={{ fontSize: 64, mb: 2 }} />
            <Typography variant="h6">Start a conversation</Typography>
            <Typography variant="body2">
              I'm here to help you find information in your documents
            </Typography>
          </Box>
        ) : (
          messages.map((message, index) => (
            <MessageBubble
              key={index}
              message={message}
              onFeedback={handleFeedback}
              onDetailedFeedback={openFeedbackDialog}
            />
          ))
        )}
        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Avatar sx={{ bgcolor: 'primary.main', mr: 2 }}>
              <BotIcon />
            </Avatar>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ ml: 2 }}>
              Thinking...
            </Typography>
          </Box>
        )}
        <div ref={messagesEndRef} />
      </Paper>

      {/* Input Area */}
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            multiline
            maxRows={4}
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
          />
          <IconButton
            color="primary"
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            sx={{ alignSelf: 'flex-end' }}
          >
            <SendIcon />
          </IconButton>
        </Box>
      </Paper>

      {/* Feedback Dialog */}
      <FeedbackDialog
        open={feedbackDialog.open}
        message={feedbackDialog.message}
        onClose={() => setFeedbackDialog({ open: false, message: null })}
        user={user}
      />
    </Box>
  );
}

function MessageBubble({ message, onFeedback, onDetailedFeedback }) {
  const isUser = message.role === 'user';
  const isError = message.role === 'error';

  return (
    <Box
      sx={{
        display: 'flex',
        mb: 3,
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}
    >
      <Avatar
        sx={{
          bgcolor: isUser ? 'secondary.main' : isError ? 'error.main' : 'primary.main',
          mr: isUser ? 0 : 2,
          ml: isUser ? 2 : 0,
        }}
      >
        {isUser ? <PersonIcon /> : <BotIcon />}
      </Avatar>
      <Box sx={{ flexGrow: 1, maxWidth: '70%' }}>
        <Paper
          sx={{
            p: 2,
            bgcolor: isUser ? 'primary.light' : isError ? 'error.light' : 'background.paper',
            color: isUser ? 'primary.contrastText' : 'text.primary',
          }}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>

          {/* Quality Scores */}
          {message.quality_scores && (
            <Box sx={{ mt: 2 }}>
              <Divider sx={{ my: 1 }} />
              <Typography variant="caption" color="text.secondary">
                Quality: {(message.quality_scores.overall * 100).toFixed(0)}% | 
                Latency: {(message.latency * 1000).toFixed(0)}ms | 
                Cost: ${message.cost.toFixed(4)}
              </Typography>
            </Box>
          )}

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" color="text.secondary">
                Sources: {message.sources.length} documents
              </Typography>
            </Box>
          )}
        </Paper>

        {/* Feedback Buttons */}
        {!isUser && !isError && message.request_id && (
          <Box sx={{ mt: 1, display: 'flex', gap: 1 }}>
            <IconButton
              size="small"
              onClick={() => onFeedback(message, 'thumbs_up')}
              disabled={message.userFeedback === 'thumbs_up'}
              color={message.userFeedback === 'thumbs_up' ? 'primary' : 'default'}
            >
              <ThumbUpIcon fontSize="small" />
            </IconButton>
            <IconButton
              size="small"
              onClick={() => onFeedback(message, 'thumbs_down')}
              disabled={message.userFeedback === 'thumbs_down'}
              color={message.userFeedback === 'thumbs_down' ? 'primary' : 'default'}
            >
              <ThumbDownIcon fontSize="small" />
            </IconButton>
            <Button
              size="small"
              onClick={() => onDetailedFeedback(message)}
            >
              Detailed Feedback
            </Button>
          </Box>
        )}
      </Box>
    </Box>
  );
}

