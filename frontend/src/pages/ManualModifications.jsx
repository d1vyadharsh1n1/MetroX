import { useState, useEffect } from 'react'
import { Typography, Button, Card, Row, Col, Table, Tag, Space, Alert, Modal, Input, Select, message, Statistic } from 'antd'
import { PlayCircleOutlined, ReloadOutlined, CheckCircleOutlined, ExclamationCircleOutlined, WarningOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { motion } from 'framer-motion'
import axios from 'axios'

const { Title, Text } = Typography
const { Option } = Select

export default function ManualModifications() {
  const [schedule, setSchedule] = useState([])
  const [loading, setLoading] = useState(false)
  const [modificationLog, setModificationLog] = useState([])
  const [selectedTrain, setSelectedTrain] = useState(null)
  const [modalVisible, setModalVisible] = useState(false)
  const [whatIfModalVisible, setWhatIfModalVisible] = useState(false)
  const [whatIfScenario, setWhatIfScenario] = useState('')
  const [customHeadway, setCustomHeadway] = useState(10)

  const fetchSchedule = async () => {
    try {
      const response = await axios.get('/api/schedule')
      setSchedule(response.data)
    } catch (error) {
      console.error('Error fetching schedule:', error)
    }
  }

  const fetchModificationLog = async () => {
    try {
      const response = await axios.get('/api/modification-log')
      setModificationLog(response.data.modification_log || [])
    } catch (error) {
      console.error('Error fetching modification log:', error)
    }
  }

  const modifyTrain = async (action, trainId) => {
    try {
      const response = await axios.post('/api/modify', {
        action: action,
        train_id: trainId
      })
      
      if (response.data.error) {
        // Show error message
        message.error(response.data.error)
      } else if (response.data.warning) {
        // Show warning message
        message.warning(response.data.warning)
        
        // If proceed_anyway is true, show a confirmation dialog
        if (response.data.proceed_anyway) {
          Modal.confirm({
            title: 'High Risk Warning',
            content: 'This train has a high failure risk. Are you sure you want to proceed?',
            onOk: async () => {
              // Proceed with the modification
              const proceedResponse = await axios.post('/api/modify', {
                action: action,
                train_id: trainId,
                force: true
              })
              handleModificationSuccess(proceedResponse.data)
            }
          })
        }
      } else if (response.data.success) {
        handleModificationSuccess(response.data)
      } else {
        // Fallback for old response format
        message.success(response.data.message)
        setModificationLog(response.data.modification_log || [])
        fetchSchedule()
      }
    } catch (error) {
      const errorData = error.response?.data
      if (errorData?.error) {
        message.error(errorData.error)
      } else {
        message.error('Modification failed')
      }
    }
  }

  const handleModificationSuccess = (data) => {
    // Update modification log and refresh schedule
    setModificationLog(data.modification_log || [])
    fetchSchedule()
  }

  const performWhatIfAnalysis = async (scenario, trainId = null) => {
    try {
      const response = await axios.post('/api/whatif', {
        scenario: scenario,
        train_id: trainId,
        headway: customHeadway
      })
      
      const analysis = response.data
      
      // Show analysis results
      if (scenario === 'force_service_analysis') {
        Modal.info({
          title: `Analysis for Train ${trainId}`,
          content: (
            <div>
              <p><strong>Current Status:</strong> {analysis.current_status}</p>
              <p><strong>Failure Risk:</strong> {analysis.failure_risk}</p>
              <p><strong>Recommendation:</strong> {analysis.recommendation}</p>
              <p><strong>Reason:</strong> {analysis.reason}</p>
            </div>
          )
        })
      } else if (scenario === 'simulate_failure') {
        Modal.info({
          title: `Failure Simulation for Train ${trainId}`,
          content: (
            <div>
              <p><strong>Current Status:</strong> {analysis.current_status}</p>
              <p><strong>Service Impact:</strong> {analysis.service_impact}</p>
              <p><strong>Available Standby:</strong> {analysis.available_standby}</p>
              {analysis.critical && <p style={{color: 'red'}}><strong>CRITICAL: No standby trains available!</strong></p>}
            </div>
          )
        })
      } else if (scenario === 'maintenance_delay') {
        Modal.info({
          title: 'Maintenance Delay Analysis',
          content: (
            <div>
              <p><strong>High-risk trains:</strong> {analysis.high_risk_trains}</p>
              <p><strong>Impact:</strong> {analysis.impact}</p>
            </div>
          )
        })
      } else if (scenario === 'headway_analysis') {
        Modal.info({
          title: 'Headway Analysis',
          content: (
            <div>
              <p><strong>New Headway:</strong> {analysis.new_headway} minutes</p>
              <p><strong>Trains needed for service:</strong> {analysis.trains_needed.toFixed(1)}</p>
              <p><strong>Total needed (including standby):</strong> {analysis.total_needed.toFixed(1)}</p>
              <p><strong>Feasible:</strong> {analysis.feasible ? 'Yes' : 'No'}</p>
              {!analysis.feasible && <p style={{color: 'red'}}><strong>Shortage:</strong> {analysis.shortage.toFixed(1)} trains</p>}
            </div>
          )
        })
      }
      
    } catch (error) {
      message.error(error.response?.data?.error || 'Analysis failed')
    }
  }

  useEffect(() => {
    fetchSchedule()
    fetchModificationLog()
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
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button 
            size="small" 
            type="primary" 
            onClick={() => {
              setSelectedTrain(record.train_id)
              setModalVisible(true)
            }}
          >
            Modify
          </Button>
          <Button 
            size="small" 
            onClick={() => performWhatIfAnalysis('force_service_analysis', record.train_id)}
          >
            Analyze
          </Button>
        </Space>
      )
    },
  ]

  const getStatusSummary = () => {
    if (!schedule.length) return { service: 0, standby: 0, ibl: 0 }
    
    return {
      service: schedule.filter(s => s.final_status === 'Service').length,
      standby: schedule.filter(s => s.final_status === 'Standby').length,
      ibl: schedule.filter(s => s.final_status === 'IBL').length
    }
  }

  const summary = getStatusSummary()

  return (
    <div>
      <Title level={2}>🔧 Manual Modifications</Title>
      
      {/* Control Panel */}
      <Card style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchSchedule}
              >
                Refresh Schedule
              </Button>
              <Button
                type="primary"
                onClick={() => setWhatIfModalVisible(true)}
              >
                What-If Analysis
              </Button>
            </Space>
          </Col>
          <Col>
            <Text type="secondary">
              Modify train assignments and perform analysis
            </Text>
          </Col>
        </Row>
      </Card>

      {/* Summary Statistics */}
      {schedule.length > 0 && (
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
        <Title level={4}>Current Schedule - Click Modify to Change Train Status</Title>
        {schedule.length > 0 ? (
          <Table
            dataSource={schedule}
            columns={columns}
            rowKey="train_id"
            pagination={false}
            size="small"
            scroll={{ x: 800 }}
          />
        ) : (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Text type="secondary">No schedule data available. Run the prediction first.</Text>
          </div>
        )}
      </Card>


      {/* Modification Log */}
      {modificationLog.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={{ marginTop: 24 }}
        >
          <Card>
            <Title level={4}>📝 Modification History</Title>
            <div style={{ 
              backgroundColor: '#f5f5f5', 
              padding: 16, 
              borderRadius: 8, 
              maxHeight: 200, 
              overflowY: 'auto',
              fontFamily: 'monospace',
              fontSize: 12
            }}>
              {modificationLog.map((log, index) => (
                <div key={index} style={{ marginBottom: 4 }}>
                  {log}
                </div>
              ))}
            </div>
          </Card>
        </motion.div>
      )}

      {/* Train Modification Modal */}
      <Modal
        title={`Modify Train ${selectedTrain}`}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedTrain && (
          <div>
            <Text strong style={{ marginBottom: 16, display: 'block' }}>
              Select modification for Train {selectedTrain}:
            </Text>
            
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button 
                type="primary" 
                block
                onClick={() => {
                  modifyTrain('force_service', selectedTrain)
                  setModalVisible(false)
                }}
              >
                Force to Service
              </Button>
              
              <Button 
                block
                onClick={() => {
                  modifyTrain('force_standby', selectedTrain)
                  setModalVisible(false)
                }}
              >
                Force to Standby
              </Button>
              
              <Button 
                danger
                block
                onClick={() => {
                  modifyTrain('force_ibl', selectedTrain)
                  setModalVisible(false)
                }}
              >
                Force to IBL
              </Button>
              
              <Button 
                block
                onClick={() => {
                  modifyTrain('reset', selectedTrain)
                  setModalVisible(false)
                }}
              >
                Reset to Predicted Status
              </Button>
            </Space>
          </div>
        )}
      </Modal>

      {/* What-If Analysis Modal */}
      <Modal
        title="What-If Analysis"
        open={whatIfModalVisible}
        onCancel={() => setWhatIfModalVisible(false)}
        footer={null}
        width={600}
      >
        <div>
          <Text strong style={{ marginBottom: 16, display: 'block' }}>
            Select analysis scenario:
          </Text>
          
          <Space direction="vertical" style={{ width: '100%' }}>
            <Button 
              block
              onClick={() => {
                setWhatIfScenario('force_service_analysis')
                setModalVisible(true)
              }}
            >
              Force Specific Train to Service
            </Button>
            
            <Button 
              block
              onClick={() => {
                setWhatIfScenario('simulate_failure')
                setModalVisible(true)
              }}
            >
              Simulate Train Failure
            </Button>
            
            <Button 
              block
              onClick={() => performWhatIfAnalysis('maintenance_delay')}
            >
              Change Maintenance Schedule
            </Button>
            
            <div>
              <Text>Adjust Service Hours/Headway:</Text>
              <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                <Input
                  type="number"
                  value={customHeadway}
                  onChange={(e) => setCustomHeadway(Number(e.target.value))}
                  placeholder="Headway in minutes"
                  style={{ width: 200 }}
                />
                <Button 
                  onClick={() => performWhatIfAnalysis('headway_analysis')}
                >
                  Analyze
                </Button>
              </div>
            </div>
          </Space>
        </div>
      </Modal>
    </div>
  )
}
