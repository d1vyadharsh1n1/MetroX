import { useState, useEffect } from 'react'
import { Typography, Button, Card, Row, Col, Statistic, Table, Tag, Space, Alert, Spin, Empty } from 'antd'
import { PlayCircleOutlined, ReloadOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import axios from 'axios'

const { Title, Text } = Typography

export default function Scheduler() {
  const [status, setStatus] = useState({
    is_running: false,
    current_step: '',
    output: [],
    error: null,
    last_execution: null
  })
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading] = useState(false)
  const [hoveredTrain, setHoveredTrain] = useState(null)
  const [selectedTrain, setSelectedTrain] = useState(null)

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
      const response = await axios.get('/api/schedule')
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

  useEffect(() => {
    fetchStatus()
    fetchPredictions()
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
      <Title level={2}>🚇 Metro Scheduler</Title>
      
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

      {/* Train Line Display */}
      {predictions.length > 0 && (
        <Card style={{ marginBottom: 24 }}>
          <Title level={4}>Train Schedule - Visual Overview</Title>
          <div style={{ position: 'relative', padding: '24px 8px 8px 8px', overflowX: 'auto', marginBottom: 24 }}>
            <div style={{ position: 'absolute', left: 0, right: 0, top: 48, height: 6, background: 'linear-gradient(90deg,#9aa7b1,#e5eaef)', borderRadius: 6 }} />
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', minWidth: 'max-content', paddingRight: '16px' }}>
              {predictions.map((train, i) => {
                const color = train.final_status === 'Service' ? '#1db954' : train.final_status === 'Standby' ? '#f0ad4e' : '#e55353'
                return (
                  <motion.div 
                    key={train.train_id} 
                    initial={{ opacity: 0, y: 10 }} 
                    animate={{ opacity: 1, y: 0 }} 
                    transition={{ delay: i*0.01 }} 
                    whileHover={{ scale: 1.06 }} 
                    style={{ cursor: 'pointer', flexShrink: 0 }}
                    onMouseEnter={() => setHoveredTrain(train)}
                    onMouseLeave={() => setHoveredTrain(null)}
                    onClick={() => setSelectedTrain(selectedTrain?.train_id === train.train_id ? null : train)}
                  >
                    <TrainCar id={train.train_id} color={color} />
                  </motion.div>
                )
              })}
            </div>
          </div>

          {/* Train Details */}
          {(hoveredTrain || selectedTrain) && (
            <Card title={`Train Details: ${(hoveredTrain || selectedTrain)?.train_id}`} style={{ marginTop: 16 }}>
              <Table
                dataSource={[(hoveredTrain || selectedTrain)]}
                columns={columns}
                pagination={false}
                size="small"
                bordered
              />
              
              {/* Additional Details */}
              <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
                <div>
                  <strong>Cleaning Slot:</strong> {(hoveredTrain || selectedTrain)?.cleaning_slot}
                </div>
                <div>
                  <strong>Stabling Position:</strong> {(hoveredTrain || selectedTrain)?.stabling_position}
                </div>
                <div>
                  <strong>RS Days from Plan:</strong> {(hoveredTrain || selectedTrain)?.rs_days_from_plan}
                </div>
                <div>
                  <strong>SIG Days from Plan:</strong> {(hoveredTrain || selectedTrain)?.sig_days_from_plan}
                </div>
                <div>
                  <strong>TEL Days from Plan:</strong> {(hoveredTrain || selectedTrain)?.tel_days_from_plan}
                </div>
                <div>
                  <strong>Branding Req Hours:</strong> {(hoveredTrain || selectedTrain)?.branding_req_hours?.toFixed(2)}
                </div>
                <div>
                  <strong>Branding Alloc Hours:</strong> {(hoveredTrain || selectedTrain)?.branding_alloc_hours?.toFixed(2)}
                </div>
                <div>
                  <strong>Estimated Shunting (mins):</strong> {(hoveredTrain || selectedTrain)?.estimated_shunting_mins}
                </div>
                <div>
                  <strong>Prev Night Shunting:</strong> {(hoveredTrain || selectedTrain)?.prev_night_shunting_count}
                </div>
                <div>
                  <strong>IoT Temp Avg (°C):</strong> {(hoveredTrain || selectedTrain)?.iot_temp_avg_c?.toFixed(1)}
                </div>
                <div>
                  <strong>HVAC Alert:</strong> {(hoveredTrain || selectedTrain)?.hvac_alert ? 'Yes' : 'No'}
                </div>
                <div>
                  <strong>Last Maintenance:</strong> {(hoveredTrain || selectedTrain)?.last_maintenance_date}
                </div>
                <div>
                  <strong>Manual Override:</strong> {(hoveredTrain || selectedTrain)?.manual_override_flag ? 'Yes' : 'No'}
                </div>
              </div>
            </Card>
          )}
        </Card>
      )}

      {/* Train Schedule Table */}
      <Card>
        <Title level={4}>Train Schedule - Detailed Table</Title>
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
          <Title level={4}>Recent Execution Logs</Title>
          <div style={{ 
            backgroundColor: '#f5f5f5', 
            padding: 16, 
            borderRadius: 8, 
            maxHeight: 200, 
            overflowY: 'auto',
            fontFamily: 'monospace',
            fontSize: 12
          }}>
            {status.output.slice(-10).map((line, index) => (
              <div key={index} style={{ marginBottom: 4 }}>
                {line}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function TrainCar({ id, color }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <svg width="80" height="32" viewBox="0 0 80 32">
        <rect x="4" y="8" rx="4" ry="4" width="72" height="16" fill="#0b1e2a" stroke={color} strokeWidth="2" />
        <rect x="10" y="10" rx="2" ry="2" width="18" height="12" fill="#e6f4ff" />
        <rect x="30" y="10" rx="2" ry="2" width="18" height="12" fill="#e6f4ff" />
        <rect x="50" y="10" rx="2" ry="2" width="18" height="12" fill="#e6f4ff" />
        <circle cx="20" cy="26" r="2" fill="#333" />
        <circle cx="60" cy="26" r="2" fill="#333" />
      </svg>
      <div style={{ marginTop: 2, fontSize: 10, fontWeight: 600 }}>{id}</div>
    </div>
  )
}