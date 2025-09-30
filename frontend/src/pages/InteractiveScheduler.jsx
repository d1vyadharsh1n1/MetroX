import { useState, useEffect } from 'react'
import { Typography, Button, Card, Row, Col, Statistic, Table, Tag, Space, Alert, Spin, Input, Modal, message } from 'antd'
import { PlayCircleOutlined, ReloadOutlined, CheckCircleOutlined, ExclamationCircleOutlined, UserOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import axios from 'axios'

const { Title, Text } = Typography
const { TextArea } = Input

export default function InteractiveScheduler() {
  const [status, setStatus] = useState({
    is_running: false,
    current_step: '',
    output: [],
    error: null,
    last_execution: null,
    waiting_for_input: false,
    input_prompt: '',
    input_options: [],
    input_type: '',
    current_data: null
  })
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(false)
  const [customInput, setCustomInput] = useState('')
  const [modalVisible, setModalVisible] = useState(false)

  const fetchStatus = async () => {
    try {
      const response = await axios.get('/api/status')
      setStatus(response.data)
    } catch (error) {
      console.error('Error fetching status:', error)
    }
  }

  const fetchPredictions = async () => {
    try {
      const response = await axios.get('/api/data/predictions')
      setPredictions(response.data)
    } catch (error) {
      console.error('Error fetching predictions:', error)
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
          fetchPredictions()
          setLoading(false)
        }
      }, 1000)
    } catch (error) {
      console.error('Error running prediction:', error)
      setLoading(false)
    }
  }

  const sendInput = async (inputValue) => {
    try {
      await axios.post('/api/input', { input: inputValue })
      message.success('Input sent successfully')
      setModalVisible(false)
      setCustomInput('')
    } catch (error) {
      message.error('Failed to send input')
      console.error('Error sending input:', error)
    }
  }

  const handleMenuOption = (option) => {
    sendInput(option.value)
  }

  const handleCustomInput = () => {
    if (customInput.trim()) {
      sendInput(customInput.trim())
    }
  }

  const handleConfirm = (value) => {
    sendInput(value)
  }

  useEffect(() => {
    fetchStatus()
    fetchPredictions()
    
    // Poll for updates every 2 seconds
    const interval = setInterval(fetchStatus, 2000)
    return () => clearInterval(interval)
  }, [])

  const columns = [
    {
      title: 'Rank',
      dataIndex: 'ranking',
      key: 'ranking',
      width: 60,
    },
    {
      title: 'Train ID',
      dataIndex: 'train_id',
      key: 'train_id',
      width: 100,
    },
    {
      title: 'Final Status',
      dataIndex: 'final_status',
      key: 'final_status',
      width: 120,
      render: (status) => {
        const color = status === 'Service' ? 'green' : status === 'Standby' ? 'orange' : 'red'
        return <Tag color={color}>{status}</Tag>
      }
    },
    {
      title: 'Predicted Status',
      dataIndex: 'predicted_status',
      key: 'predicted_status',
      width: 120,
      render: (status) => {
        const color = status === 'Service' ? 'green' : status === 'Standby' ? 'orange' : 'red'
        return <Tag color={color}>{status}</Tag>
      }
    },
    {
      title: 'Failure Risk',
      dataIndex: 'predicted_failure_risk',
      key: 'predicted_failure_risk',
      width: 100,
      render: (value) => value ? (value * 100).toFixed(1) + '%' : 'N/A'
    },
    {
      title: 'Next Day Mileage',
      dataIndex: 'predicted_next_day_mileage',
      key: 'predicted_next_day_mileage',
      width: 150,
      render: (value) => value ? value.toFixed(2) + ' km' : 'N/A'
    },
    {
      title: 'Depot',
      dataIndex: 'depot',
      key: 'depot',
      width: 120,
    },
  ]

  const getStatusSummary = () => {
    if (!predictions.length) return { service: 0, standby: 0, ibl: 0 }
    
    return {
      service: predictions.filter(p => p.final_status === 'Service').length,
      standby: predictions.filter(p => p.final_status === 'Standby').length,
      ibl: predictions.filter(p => p.final_status === 'IBL').length
    }
  }

  const summary = getStatusSummary()

  return (
    <div>
      <Title level={2}>🎮 Interactive Metro Scheduler</Title>
      
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
                {status.is_running ? 'Running...' : 'Run Interactive Prediction'}
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => {
                  fetchStatus()
                  fetchPredictions()
                }}
              >
                Refresh
              </Button>
            </Space>
          </Col>
          <Col>
            {status.last_execution && (
              <Text type="secondary">
                Last run: {new Date(status.last_execution).toLocaleString()}
              </Text>
            )}
          </Col>
        </Row>

        {/* Status Display */}
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

      {/* Interactive Input Panel */}
      {status.waiting_for_input && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <Card style={{ marginBottom: 24, border: '2px solid #1890ff' }}>
            <Title level={4} style={{ color: '#1890ff' }}>
              <UserOutlined /> Interactive Input Required
            </Title>
            <Text strong style={{ fontSize: 16, marginBottom: 16, display: 'block' }}>
              {status.input_prompt}
            </Text>
            
            {status.input_type === 'menu' && (
              <div>
                <Text>Select an option:</Text>
                <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {status.input_options.map((option) => (
                    <Button
                      key={option.value}
                      onClick={() => handleMenuOption(option)}
                      style={{ marginBottom: 8 }}
                    >
                      {option.value}. {option.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            
            {status.input_type === 'train_id' && (
              <div>
                <Text>Enter Train ID:</Text>
                <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                  <Input
                    placeholder="e.g., KM-T101"
                    value={customInput}
                    onChange={(e) => setCustomInput(e.target.value.toUpperCase())}
                    onPressEnter={handleCustomInput}
                    style={{ width: 200 }}
                  />
                  <Button type="primary" onClick={handleCustomInput}>
                    Submit
                  </Button>
                </div>
              </div>
            )}
            
            {status.input_type === 'confirm' && (
              <div>
                <Text>Confirm your choice:</Text>
                <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                  {status.input_options.map((option) => (
                    <Button
                      key={option.value}
                      type={option.value === 'y' ? 'primary' : 'default'}
                      onClick={() => handleConfirm(option.value)}
                    >
                      {option.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            
            <div style={{ marginTop: 16 }}>
              <Button
                type="dashed"
                onClick={() => setModalVisible(true)}
              >
                Custom Input
              </Button>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Summary Statistics */}
      {predictions.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={8}>
            <Card>
              <Statistic
                title="Service Trains"
                value={summary.service}
                valueStyle={{ color: '#1db954' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={8}>
            <Card>
              <Statistic
                title="Standby Trains"
                value={summary.standby}
                valueStyle={{ color: '#f0ad4e' }}
                prefix={<ExclamationCircleOutlined />}
              />
            </Card>
          </Col>
          <Col xs={8}>
            <Card>
              <Statistic
                title="IBL Trains"
                value={summary.ibl}
                valueStyle={{ color: '#e55353' }}
                prefix={<ExclamationCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Train Schedule Table */}
      <Card>
        <Title level={4}>Train Schedule - Ranked by Status</Title>
        {predictions.length > 0 ? (
          <Table
            dataSource={predictions}
            columns={columns}
            rowKey="train_id"
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Text type="secondary">No prediction data available. Run the prediction to generate the schedule.</Text>
          </div>
        )}
      </Card>

      {/* Execution Logs Preview */}
      {status.output.length > 0 && (
        <Card style={{ marginTop: 24 }}>
          <Title level={4}>Live Execution Logs</Title>
          <div style={{ 
            backgroundColor: '#f5f5f5', 
            padding: 16, 
            borderRadius: 8, 
            maxHeight: 300, 
            overflowY: 'auto',
            fontFamily: 'monospace',
            fontSize: 12
          }}>
            {status.output.slice(-20).map((line, index) => (
              <div key={index} style={{ marginBottom: 4 }}>
                {line}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Custom Input Modal */}
      <Modal
        title="Custom Input"
        open={modalVisible}
        onOk={handleCustomInput}
        onCancel={() => setModalVisible(false)}
        okText="Send"
        cancelText="Cancel"
      >
        <div style={{ marginBottom: 16 }}>
          <Text>Enter custom input for the script:</Text>
        </div>
        <TextArea
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          placeholder="Enter your input here..."
          rows={3}
        />
      </Modal>
    </div>
  )
}
