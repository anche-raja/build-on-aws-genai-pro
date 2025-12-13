import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Chip,
  Divider,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  QueryStats as QueryIcon,
  AttachMoney as CostIcon,
  Speed as SpeedIcon,
  ThumbUp as ThumbUpIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export default function AdminDashboard({ user }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real implementation, fetch metrics from CloudWatch or your API
    // For now, using mock data
    const mockMetrics = {
      summary: {
        totalQueries: 12453,
        averageLatency: 1.23,
        totalCost: 156.78,
        satisfaction: 85.2,
        piiDetected: 23,
        guardrailBlocks: 5,
      },
      queryTrend: [
        { time: '00:00', queries: 120 },
        { time: '04:00', queries: 80 },
        { time: '08:00', queries: 350 },
        { time: '12:00', queries: 420 },
        { time: '16:00', queries: 380 },
        { time: '20:00', queries: 200 },
      ],
      modelUsage: [
        { name: 'Simple (Instant)', value: 7000, cost: 20 },
        { name: 'Standard (Claude 2)', value: 4000, cost: 80 },
        { name: 'Advanced (Sonnet)', value: 1453, cost: 56.78 },
      ],
      qualityScores: [
        { metric: 'Relevance', score: 88 },
        { metric: 'Coherence', score: 82 },
        { metric: 'Completeness', score: 85 },
        { metric: 'Accuracy', score: 91 },
        { metric: 'Conciseness', score: 79 },
        { metric: 'Groundedness', score: 87 },
      ],
      recentFeedback: [
        { id: 1, rating: 5, comment: 'Very helpful!', timestamp: '2 mins ago' },
        { id: 2, rating: 4, comment: 'Good but could be faster', timestamp: '15 mins ago' },
        { id: 3, rating: 5, comment: 'Excellent response', timestamp: '1 hour ago' },
      ],
    };

    setTimeout(() => {
      setMetrics(mockMetrics);
      setLoading(false);
    }, 1000);
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Admin Dashboard
      </Typography>
      <Typography variant="body2" color="text.secondary" gutterBottom sx={{ mb: 3 }}>
        Real-time system metrics and analytics
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Queries"
            value={metrics.summary.totalQueries.toLocaleString()}
            icon={<QueryIcon />}
            color="#1976d2"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Avg Latency"
            value={`${metrics.summary.averageLatency}s`}
            icon={<SpeedIcon />}
            color="#2e7d32"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Total Cost"
            value={`$${metrics.summary.totalCost.toFixed(2)}`}
            icon={<CostIcon />}
            color="#ed6c02"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            title="Satisfaction"
            value={`${metrics.summary.satisfaction}%`}
            icon={<ThumbUpIcon />}
            color="#9c27b0"
          />
        </Grid>
      </Grid>

      {/* Governance Metrics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <SecurityIcon sx={{ mr: 1, color: 'warning.main' }} />
              <Typography variant="h6">Governance</Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Chip
                label={`PII Detected: ${metrics.summary.piiDetected}`}
                color="warning"
                variant="outlined"
              />
              <Chip
                label={`Guardrail Blocks: ${metrics.summary.guardrailBlocks}`}
                color="error"
                variant="outlined"
              />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Charts */}
      <Grid container spacing={3}>
        {/* Query Trend */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Query Trend (Last 24 Hours)
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={metrics.queryTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="queries" stroke="#1976d2" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Model Usage */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Model Usage
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={metrics.modelUsage}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.name}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {metrics.modelUsage.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <Divider sx={{ my: 2 }} />
            <Typography variant="caption" color="text.secondary">
              Cost breakdown:
            </Typography>
            {metrics.modelUsage.map((model, index) => (
              <Typography key={index} variant="body2">
                {model.name}: ${model.cost.toFixed(2)}
              </Typography>
            ))}
          </Paper>
        </Grid>

        {/* Quality Scores */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Quality Scores
            </Typography>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={metrics.qualityScores}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="metric" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                <Bar dataKey="score" fill="#1976d2" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>

        {/* Recent Feedback */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Feedback
            </Typography>
            {metrics.recentFeedback.map((feedback) => (
              <Box key={feedback.id} sx={{ mb: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    {'⭐'.repeat(feedback.rating)}
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {feedback.timestamp}
                  </Typography>
                </Box>
                <Typography variant="body2">{feedback.comment}</Typography>
              </Box>
            ))}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

function MetricCard({ title, value, icon, color }) {
  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 48,
              height: 48,
              borderRadius: 2,
              bgcolor: `${color}20`,
              color: color,
              mr: 2,
            }}
          >
            {icon}
          </Box>
          <Box>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h5">{value}</Typography>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

