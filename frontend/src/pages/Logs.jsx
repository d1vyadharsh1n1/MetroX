import { useState, useEffect } from 'react'
import { Typography, Card, Button, Space, Alert, Spin, Tag, Timeline } from 'antd'
import { ReloadOutlined, PlayCircleOutlined, CheckCircleOutlined, ExclamationCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import axios from 'axios'

const { Title, Text } = Typography

export default function Logs() {
  const [status, setStatus] = useState({
    is_running: false,
    current_step: '',
    output: [],
    error: null,
    last_execution: null
  })
  const [loading, setLoading] = useState(false)

  const fetchStatus = async () => {
    try {
      const response = await axios.get('/api/status')
      setStatus(response.data)
    } catch (error) {
      console.error('Error fetching status:', error)
    }
  }

  const runPrediction = async () => {
    setLoading(true)
    try {
      await axios.post('/api/predict')
      // Start polling for status updates
      const interval = setInterval(() => {
        fetchStatus()
        if (!status.is_running) {
          clearInterval(interval)
          setLoading(false)
        }
      }, 1000)
    } catch (error) {
      console.error('Error running prediction:', error)
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    // Poll for updates every 2 seconds
    const interval = setInterval(fetchStatus, 2000)
    return () => clearInterval(interval)
  }, [])

  const getLogIcon = (line) => {
    if (line.includes('✅') || line.includes('completed successfully')) {
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />
    } else if (line.includes('❌') || line.includes('failed') || line.includes('error')) {
      return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
    } else if (line.includes('Starting') || line.includes('Running')) {
      return <PlayCircleOutlined style={{ color: '#1890ff' }} />
    } else {
      return <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
    }
  }

  const getLogColor = (line) => {
    if (line.includes('✅') || line.includes('completed successfully')) {
      return 'green'
    } else if (line.includes('❌') || line.includes('failed') || line.includes('error')) {
      return 'red'
    } else if (line.includes('Starting') || line.includes('Running')) {
      return 'blue'
    } else {
      return 'gray'
    }
  }

  return (
    <div>
      <Title level={2}>📋 Execution Logs</Title>
      
      {/* Control Panel */}
      <Card style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button
                type="primary"
                size="large"
                icon={<PlayCircleOutlined />}
                onClick={runPrediction}
                loading={loading || status.is_running}
                disabled={status.is_running}
              >
                {status.is_running ? 'Running...' : 'Run Prediction'}
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchStatus}
              >
                Refresh Logs
              </Button>
            </Space>
          </Col>
          <Col>
            {status.last_execution && (
              <Text type="secondary">
                Last execution: {new Date(status.last_execution).toLocaleString()}
              </Text>
            )}
          </Col>
        </Row>

        {/* Current Status */}
        {status.is_running && (
          <div style={{ marginTop: 16 }}>
            <Alert
              message={`Currently running: ${status.current_step}`}
              type="info"
              showIcon
              icon={<Spin size="small" />}
            />
          </div>
        )}

        {status.error && (
          <div style={{ marginTop: 16 }}>
            <Alert
              message="Execution Error"
              description={status.error}
              type="error"
              showIcon
              icon={<ExclamationCircleOutlined />}
            />
          </div>
        )}
      </Card>

      {/* Execution Timeline */}
      <Card>
        <Title level={4}>Execution Timeline</Title>
        {status.output.length > 0 ? (
          <div style={{ maxHeight: 600, overflowY: 'auto' }}>
            <Timeline
              items={status.output.map((line, index) => ({
                dot: getLogIcon(line),
                color: getLogColor(line),
                children: (
                  <div style={{ fontFamily: 'monospace', fontSize: 12 }}>
                    <Text code>{line}</Text>
                  </div>
                )
              }))}
            />
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Text type="secondary">No execution logs available. Run the prediction to see logs.</Text>
          </div>
        )}
      </Card>

      {/* Raw Log Output */}
      {status.output.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{ marginTop: 24 }}
        >
          <Card>
            <Title level={4}>Raw Log Output</Title>
            <div style={{ 
              backgroundColor: '#f5f5f5', 
              padding: 16, 
              borderRadius: 8, 
              maxHeight: 400, 
              overflowY: 'auto',
              fontFamily: 'monospace',
              fontSize: 12,
              whiteSpace: 'pre-wrap'
            }}>
              {status.output.map((line, index) => (
                <div key={index} style={{ marginBottom: 2 }}>
                  {line}
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {/* System Information */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        style={{ marginTop: 24 }}
      >
        <Card>
          <Title level={4}>System Information</Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Card size="small">
                <Text strong>Scripts Directory</Text>
                <br />
                <Text code>MetroX_309/ai_railway_project/scripts/</Text>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card size="small">
                <Text strong>Data Directory</Text>
                <br />
                <Text code>MetroX_309/ai_railway_project/data/</Text>
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card size="small">
                <Text strong>Execution Timeout</Text>
                <br />
                <Text code>5 minutes per script</Text>
              </Card>
            </Col>
          </Row>
        </Card>
      </motion.div>
    </div>
  )
}
